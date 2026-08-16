from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.chat import ChatMessage, ChatSession, QuickQuestion
from app.models.user import User
from app.schemas.common import ok
from app.services.knowledge import search_knowledge
from app.services.llm import stream_llm_or_fallback

router = APIRouter(prefix="/ai", tags=["ai"])

SENSITIVE = ("自杀", "爆炸制作", "洗钱")
OFF_TOPIC = ("今天股市", "帮我写情书", "彩票号码")


class ChatBody(BaseModel):
    question: str
    session_id: str | None = None


class SessionBody(BaseModel):
    title: str = "新会话"


class TitleBody(BaseModel):
    title: str


class FeedbackBody(BaseModel):
    feedback: str
    reason: str = ""


class QuickBody(BaseModel):
    category: str
    question: str
    roles: list[str] = ["Employee", "SafetyOfficer"]
    is_hot: bool = False


@router.get("/capabilities")
def capabilities(_: User = Depends(get_current_user)):
    from app.config import settings
    from app.services.knowledge import kb_available

    return ok(
        {
            "agent": "LangChain create_agent",
            "model_configured": bool(settings.llm_api_key and settings.llm_base_url),
            "model": settings.llm_model if settings.llm_api_key else "知识库证据模式",
            "knowledge_base": kb_available(),
        }
    )


def session_to_dict(item: ChatSession, last: str = "") -> dict:
    return {
        "session_id": item.id,
        "title": item.title,
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
        "last_message": last,
    }


@router.post("/sessions")
def create_session(body: SessionBody | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = db.scalar(select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user.id)) or 0
    if count >= 100:
        return JSONResponse({"code": 40204, "message": "会话数量已达上限（100 个）", "data": None}, 400)
    item = ChatSession(id=str(uuid.uuid4()), user_id=user.id, title=(body.title if body else "新会话"))
    db.add(item)
    db.commit()
    return ok(session_to_dict(item))


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.scalars(
        select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc())
    ).all()
    result = []
    for item in items:
        last = db.scalar(
            select(ChatMessage.content)
            .where(ChatMessage.session_id == item.id)
            .order_by(ChatMessage.id.desc())
            .limit(1)
        )
        result.append(session_to_dict(item, last or ""))
    return ok(result)


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        return JSONResponse({"code": 40402, "message": "会话不存在", "data": None}, 404)
    messages = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id)).all()
    return ok(
        [
            {
                "message_id": item.id,
                "role": item.role,
                "content": item.content,
                "citations": json.loads(item.citations_json or "[]"),
                "feedback": item.feedback,
                "created_at": item.created_at.isoformat() if item.created_at else "",
            }
            for item in messages
        ]
    )


@router.put("/sessions/{session_id}")
def rename_session(session_id: str, body: TitleBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        return JSONResponse({"code": 40402, "message": "会话不存在", "data": None}, 404)
    session.title = body.title
    db.commit()
    return ok(session_to_dict(session))


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        return JSONResponse({"code": 40402, "message": "会话不存在", "data": None}, 404)
    db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    db.delete(session)
    db.commit()
    return ok(None, "已删除")


@router.post("/chat")
def chat(body: ChatBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    question = body.question.strip()
    if any(word in question for word in SENSITIVE):
        return JSONResponse({"code": 40201, "message": "问题包含敏感内容", "data": None}, 400)
    if any(word in question for word in OFF_TOPIC):
        return JSONResponse({"code": 40202, "message": "非安全相关问题", "data": None}, 400)

    session = db.get(ChatSession, body.session_id) if body.session_id else None
    if session and session.user_id != user.id:
        return JSONResponse({"code": 40402, "message": "会话不存在", "data": None}, 404)
    if not session:
        session = ChatSession(id=str(uuid.uuid4()), user_id=user.id, title=question[:24] or "新会话")
        db.add(session)
        db.flush()

    db.add(ChatMessage(session_id=session.id, role="user", content=question))
    hits = search_knowledge(question, limit=5)
    history_rows = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.id.desc()).limit(8)
    ).all()
    history = [{"role": row.role, "content": row.content} for row in reversed(history_rows)]
    answer = "".join(stream_llm_or_fallback(question, hits, history))
    assistant = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        citations_json=json.dumps(hits, ensure_ascii=False),
    )
    db.add(assistant)
    if session.title == "新会话":
        session.title = question[:24]
    db.commit()

    def event_stream():
        yield f"data: {json.dumps({'session_id': session.id, 'message_id': assistant.id, 'content': answer, 'citations': hits}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/sync")
def chat_sync(body: ChatBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    question = body.question.strip()
    if any(word in question for word in SENSITIVE):
        return JSONResponse({"code": 40201, "message": "问题包含敏感内容", "data": None}, 400)
    if any(word in question for word in OFF_TOPIC):
        return JSONResponse({"code": 40202, "message": "非安全相关问题", "data": None}, 400)
    session = db.get(ChatSession, body.session_id) if body.session_id else None
    if session and session.user_id != user.id:
        return JSONResponse({"code": 40402, "message": "会话不存在", "data": None}, 404)
    if not session:
        session = ChatSession(id=str(uuid.uuid4()), user_id=user.id, title=question[:24] or "新会话")
        db.add(session)
        db.flush()
    db.add(ChatMessage(session_id=session.id, role="user", content=question))
    hits = search_knowledge(question, limit=5)
    history_rows = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.id.desc()).limit(8)
    ).all()
    history = [{"role": row.role, "content": row.content} for row in reversed(history_rows)]
    answer = "".join(stream_llm_or_fallback(question, hits, history))
    assistant = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        citations_json=json.dumps(hits, ensure_ascii=False),
    )
    db.add(assistant)
    db.commit()
    return ok(
        {
            "session_id": session.id,
            "message_id": assistant.id,
            "content": answer,
            "citations": hits,
        }
    )


@router.get("/quick-questions")
def quick_questions(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = db.scalars(select(QuickQuestion).order_by(QuickQuestion.is_hot.desc(), QuickQuestion.id)).all()
    return ok(
        [
            {
                "id": item.id,
                "category": item.category,
                "question": item.question,
                "roles": json.loads(item.roles_json),
                "is_hot": bool(item.is_hot),
            }
            for item in items
        ]
    )


@router.post("/quick-questions")
def create_quick(body: QuickBody, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin"))):
    item = QuickQuestion(
        category=body.category,
        question=body.question,
        roles_json=json.dumps(body.roles, ensure_ascii=False),
        is_hot=1 if body.is_hot else 0,
    )
    db.add(item)
    db.commit()
    return ok({"id": item.id})


@router.post("/messages/{message_id}/feedback")
def feedback(message_id: int, body: FeedbackBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = db.get(ChatMessage, message_id)
    if not message:
        return JSONResponse({"code": 40400, "message": "消息不存在", "data": None}, 404)
    if message.feedback:
        return JSONResponse({"code": 40012, "message": "重复评价", "data": None}, 400)
    message.feedback = body.feedback
    db.commit()
    return ok(None, "已记录")
