from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.exam import ExamAttempt, ExamPaper, Question
from app.models.user import User
from app.schemas.common import ok, paginate
from app.services.exam_grade import grade_question, parse_json
from app.services.knowledge import search_knowledge

router = APIRouter(prefix="/exam", tags=["exam"])


class QuestionBody(BaseModel):
    type: str
    content: str
    options: dict = {}
    answer: str
    explanation: str
    score: float = 2
    difficulty: str = "medium"
    category: str = "安全生产"
    tags: list[str] = []
    status: str = "published"


class PaperBody(BaseModel):
    title: str
    description: str = ""
    duration_minutes: int = 60
    pass_score: float = 60
    question_ids: list[int] = []
    start_at: str = ""
    end_at: str = ""
    max_attempts: int = 2


class GenerateBody(BaseModel):
    knowledge_points: list[str] = []
    types: list[str] = ["single_choice", "true_false"]
    count: int = 5
    difficulty: str = "medium"


class AnswerBody(BaseModel):
    answers: dict[str, str]


class ReviewBody(BaseModel):
    result: str
    comment: str = ""


def question_public(item: Question, hide_answer: bool = False) -> dict:
    data = {
        "question_id": item.id,
        "type": item.type,
        "content": item.content,
        "options": parse_json(item.options_json, {}),
        "score": item.score,
        "difficulty": item.difficulty,
        "category": item.category,
        "tags": parse_json(item.tags_json, []),
        "status": item.status,
    }
    if not hide_answer:
        data["answer"] = item.answer
        data["explanation"] = item.explanation
    return data


@router.get("/questions")
def list_questions(
    page: int = 1,
    page_size: int = 20,
    type: str = "",
    difficulty: str = "",
    status: str = "",
    keyword: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "SafetyOfficer")),
):
    stmt = select(Question)
    if type:
        stmt = stmt.where(Question.type == type)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    if status:
        stmt = stmt.where(Question.status == status)
    if keyword:
        stmt = stmt.where(Question.content.like(f"%{keyword}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Question.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ok(paginate([question_public(item) for item in items], total, page, page_size))


@router.post("/questions")
def create_question(body: QuestionBody, db: Session = Depends(get_db), user: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    item = Question(
        type=body.type,
        content=body.content,
        options_json=json.dumps(body.options, ensure_ascii=False),
        answer=body.answer,
        explanation=body.explanation,
        score=body.score,
        difficulty=body.difficulty,
        category=body.category,
        tags_json=json.dumps(body.tags, ensure_ascii=False),
        status=body.status,
        created_by=user.id,
    )
    db.add(item)
    db.commit()
    return ok(question_public(item))


@router.get("/questions/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    item = db.get(Question, question_id)
    if not item:
        return JSONResponse({"code": 40404, "message": "题目不存在", "data": None}, 404)
    return ok(question_public(item))


@router.put("/questions/{question_id}")
def update_question(question_id: int, body: QuestionBody, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    item = db.get(Question, question_id)
    if not item:
        return JSONResponse({"code": 40404, "message": "题目不存在", "data": None}, 404)
    item.type = body.type
    item.content = body.content
    item.options_json = json.dumps(body.options, ensure_ascii=False)
    item.answer = body.answer
    item.explanation = body.explanation
    item.score = body.score
    item.difficulty = body.difficulty
    item.category = body.category
    item.tags_json = json.dumps(body.tags, ensure_ascii=False)
    item.status = body.status
    db.commit()
    return ok(question_public(item))


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    item = db.get(Question, question_id)
    if not item:
        return JSONResponse({"code": 40404, "message": "题目不存在", "data": None}, 404)
    papers = db.scalars(select(ExamPaper)).all()
    for paper in papers:
        if question_id in parse_json(paper.question_ids_json, []):
            return JSONResponse({"code": 40021, "message": "题目已被试卷引用，不可删除", "data": None}, 400)
    db.delete(item)
    db.commit()
    return ok(None, "已删除")


@router.post("/questions/check-duplicate")
def check_duplicate(body: QuestionBody, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    items = db.scalars(select(Question)).all()
    similar = []
    needle = body.content[:20]
    for item in items:
        if needle and needle in item.content:
            similar.append({"question_id": item.id, "content": item.content, "similarity": 0.8})
    return ok({"has_duplicate": bool(similar), "similar_questions": similar[:5]})


@router.post("/ai/generate")
def generate_questions(body: GenerateBody, db: Session = Depends(get_db), user: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    created = []
    points = body.knowledge_points or ["安全生产法"]
    for index in range(body.count):
        point = points[index % len(points)]
        hits = search_knowledge(point, limit=1)
        snippet = hits[0]["snippet"][:80] if hits else "安全生产管理基本要求"
        qtype = body.types[index % len(body.types)]
        if qtype == "true_false":
            item = Question(
                type="true_false",
                content=f"判断：围绕「{point}」，现场必须落实安全技术交底和防护措施。",
                options_json=json.dumps({"A": "正确", "B": "错误"}, ensure_ascii=False),
                answer="正确",
                explanation=snippet or "依据安全生产管理制度。",
                score=2,
                difficulty=body.difficulty if body.difficulty != "mixed" else "medium",
                category=point,
                tags_json=json.dumps([point, "AI出题"], ensure_ascii=False),
                status="pending_review",
                created_by=user.id,
            )
        elif qtype == "multi_choice":
            item = Question(
                type="multi_choice",
                content=f"围绕「{point}」，现场应落实的安全措施包括哪些？",
                options_json=json.dumps(
                    {"A": "按规范设置防护", "B": "保存安全技术交底记录", "C": "隐患整改后复查", "D": "以口头说明代替验收"},
                    ensure_ascii=False,
                ),
                answer="ABC",
                explanation=snippet or "应落实防护、交底和隐患闭环要求。",
                score=5,
                difficulty=body.difficulty if body.difficulty != "mixed" else "medium",
                category=point,
                tags_json=json.dumps([point, "AI出题"], ensure_ascii=False),
                status="pending_review",
                created_by=user.id,
            )
        elif qtype == "fill_blank":
            item = Question(
                type="fill_blank",
                content=f"围绕「{point}」，作业前应完成安全技术（ ），作业后应完成隐患闭环。",
                options_json="{}",
                answer="交底",
                explanation=snippet or "作业前必须完成安全技术交底。",
                score=5,
                difficulty=body.difficulty if body.difficulty != "mixed" else "medium",
                category=point,
                tags_json=json.dumps([point, "AI出题"], ensure_ascii=False),
                status="pending_review",
                created_by=user.id,
            )
        elif qtype == "essay":
            item = Question(
                type="essay",
                content=f"简述「{point}」相关隐患从发现到闭环的处置步骤。",
                options_json="{}",
                answer="立即处置或停工、上报、制定整改措施、复查验收并留存记录",
                explanation=snippet or "应形成发现、处置、整改、复查和归档的完整闭环。",
                score=10,
                difficulty=body.difficulty if body.difficulty != "mixed" else "medium",
                category=point,
                tags_json=json.dumps([point, "AI出题"], ensure_ascii=False),
                status="pending_review",
                created_by=user.id,
            )
        else:
            item = Question(
                type="single_choice",
                content=f"关于「{point}」，下列说法正确的是？",
                options_json=json.dumps(
                    {"A": "应按规范落实防护并保存交底记录", "B": "可以凭经验简化防护", "C": "无需验收即可复工", "D": "隐患可以口头闭环"},
                    ensure_ascii=False,
                ),
                answer="A",
                explanation=snippet or "必须依法依规落实防护与闭环。",
                score=2,
                difficulty=body.difficulty if body.difficulty != "mixed" else "medium",
                category=point,
                tags_json=json.dumps([point, "AI出题"], ensure_ascii=False),
                status="pending_review",
                created_by=user.id,
            )
        db.add(item)
        db.flush()
        created.append(question_public(item))
    db.commit()
    return ok(created)


@router.get("/review/pending")
def pending_review(db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    items = db.scalars(select(Question).where(Question.status == "pending_review")).all()
    return ok([question_public(item) for item in items])


@router.post("/review/{question_id}")
def review_question(question_id: int, body: ReviewBody, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    item = db.get(Question, question_id)
    if not item:
        return JSONResponse({"code": 40404, "message": "题目不存在", "data": None}, 404)
    item.status = "published" if body.result == "approved" else "rejected"
    db.commit()
    return ok(question_public(item))


@router.get("/papers")
def list_papers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ExamPaper)
    if user.role == "Employee":
        stmt = stmt.where(ExamPaper.status == "published")
    items = db.scalars(stmt.order_by(ExamPaper.id.desc())).all()
    return ok(
        [
            {
                "paper_id": item.id,
                "title": item.title,
                "description": item.description,
                "duration_minutes": item.duration_minutes,
                "pass_score": item.pass_score,
                "status": item.status,
                "question_count": len(parse_json(item.question_ids_json, [])),
                "start_at": item.start_at,
                "end_at": item.end_at,
            }
            for item in items
        ]
    )


@router.post("/papers")
def create_paper(body: PaperBody, db: Session = Depends(get_db), user: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    item = ExamPaper(
        title=body.title,
        description=body.description,
        duration_minutes=body.duration_minutes,
        pass_score=body.pass_score,
        question_ids_json=json.dumps(body.question_ids),
        start_at=body.start_at,
        end_at=body.end_at,
        max_attempts=body.max_attempts,
        status="draft",
        created_by=user.id,
    )
    db.add(item)
    db.commit()
    return ok({"paper_id": item.id, "status": item.status})


@router.get("/papers/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ExamPaper, paper_id)
    if not item:
        return JSONResponse({"code": 40403, "message": "试卷不存在", "data": None}, 404)
    questions = []
    for qid in parse_json(item.question_ids_json, []):
        question = db.get(Question, qid)
        if question:
            questions.append(question_public(question, hide_answer=True))
    return ok(
        {
            "paper_id": item.id,
            "title": item.title,
            "description": item.description,
            "duration_minutes": item.duration_minutes,
            "pass_score": item.pass_score,
            "status": item.status,
            "questions": questions,
        }
    )


@router.put("/papers/{paper_id}")
def update_paper(
    paper_id: int,
    body: PaperBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "SafetyOfficer")),
):
    item = db.get(ExamPaper, paper_id)
    if not item:
        return JSONResponse({"code": 40403, "message": "试卷不存在", "data": None}, 404)
    if item.status != "draft":
        return JSONResponse({"code": 40026, "message": "已发布试卷不可修改", "data": None}, 400)
    item.title = body.title
    item.description = body.description
    item.duration_minutes = body.duration_minutes
    item.pass_score = body.pass_score
    item.question_ids_json = json.dumps(body.question_ids)
    item.start_at = body.start_at
    item.end_at = body.end_at
    item.max_attempts = body.max_attempts
    db.commit()
    return ok({"paper_id": item.id, "status": item.status})


@router.post("/papers/{paper_id}/publish")
def publish_paper(paper_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    item = db.get(ExamPaper, paper_id)
    if not item:
        return JSONResponse({"code": 40403, "message": "试卷不存在", "data": None}, 404)
    item.status = "published"
    db.commit()
    return ok({"paper_id": item.id, "status": item.status})


@router.get("/my-exams")
def my_exams(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    papers = db.scalars(select(ExamPaper).where(ExamPaper.status == "published")).all()
    result = []
    for paper in papers:
        attempts = db.scalars(
            select(ExamAttempt).where(ExamAttempt.paper_id == paper.id, ExamAttempt.user_id == user.id)
        ).all()
        result.append(
            {
                "paper_id": paper.id,
                "title": paper.title,
                "duration_minutes": paper.duration_minutes,
                "pass_score": paper.pass_score,
                "attempt_count": len(attempts),
                "max_attempts": paper.max_attempts,
                "best_score": max((item.score or 0 for item in attempts), default=None),
            }
        )
    return ok(result)


@router.post("/my-exams/{paper_id}/start")
def start_exam(paper_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    paper = db.get(ExamPaper, paper_id)
    if not paper or paper.status != "published":
        return JSONResponse({"code": 40403, "message": "试卷不存在", "data": None}, 404)
    attempts = db.scalars(select(ExamAttempt).where(ExamAttempt.paper_id == paper_id, ExamAttempt.user_id == user.id)).all()
    if any(item.passed == 1 for item in attempts):
        return JSONResponse({"code": 40024, "message": "已通过考试不可重考", "data": None}, 400)
    if len(attempts) >= paper.max_attempts:
        return JSONResponse({"code": 40023, "message": "重考次数已用完", "data": None}, 400)
    existing = next((item for item in attempts if item.status == "in_progress"), None)
    if existing:
        attempt = existing
    else:
        attempt = ExamAttempt(paper_id=paper.id, user_id=user.id)
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    questions = []
    for qid in parse_json(paper.question_ids_json, []):
        question = db.get(Question, qid)
        if question:
            questions.append(question_public(question, hide_answer=True))
    return ok(
        {
            "attempt_id": attempt.id,
            "paper_id": paper.id,
            "title": paper.title,
            "duration_minutes": paper.duration_minutes,
            "questions": questions,
            "answers": parse_json(attempt.answers_json, {}),
        }
    )


@router.put("/attempts/{attempt_id}/answers")
def save_answers(attempt_id: int, body: AnswerBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        return JSONResponse({"code": 40400, "message": "考试记录不存在", "data": None}, 404)
    if attempt.status != "in_progress":
        return JSONResponse({"code": 40025, "message": "已交卷不可再次提交", "data": None}, 400)
    attempt.answers_json = json.dumps(body.answers, ensure_ascii=False)
    db.commit()
    return ok(None, "已保存")


@router.post("/attempts/{attempt_id}/submit")
def submit_exam(attempt_id: int, body: AnswerBody | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        return JSONResponse({"code": 40400, "message": "考试记录不存在", "data": None}, 404)
    if attempt.status != "in_progress":
        return JSONResponse({"code": 40025, "message": "已交卷不可再次提交", "data": None}, 400)
    answers = body.answers if body else parse_json(attempt.answers_json, {})
    paper = db.get(ExamPaper, attempt.paper_id)
    total = 0.0
    earned = 0.0
    details = []
    for qid in parse_json(paper.question_ids_json if paper else "[]", []):
        question = db.get(Question, qid)
        if not question:
            continue
        total += question.score
        score, correct = grade_question(question, answers.get(str(qid), answers.get(qid, "")))
        if question.type == "essay":
            details.append({"question_id": qid, "auto": False, "score": 0, "max": question.score})
        else:
            earned += score
            details.append({"question_id": qid, "auto": True, "correct": correct, "score": score, "max": question.score})
    percent = round((earned / total) * 100, 1) if total else 0
    attempt.answers_json = json.dumps(answers, ensure_ascii=False)
    attempt.score = percent
    attempt.passed = 1 if paper and percent >= paper.pass_score else 0
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(UTC)
    db.commit()
    return ok({"attempt_id": attempt.id, "score": percent, "passed": bool(attempt.passed), "details": details})


@router.get("/attempts/{attempt_id}/result")
def exam_result(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt or (attempt.user_id != user.id and user.role == "Employee"):
        return JSONResponse({"code": 40400, "message": "考试记录不存在", "data": None}, 404)
    paper = db.get(ExamPaper, attempt.paper_id)
    answers = parse_json(attempt.answers_json, {})
    items = []
    for qid in parse_json(paper.question_ids_json if paper else "[]", []):
        question = db.get(Question, qid)
        if not question:
            continue
        user_answer = answers.get(str(qid), answers.get(qid, ""))
        score, correct = grade_question(question, user_answer)
        items.append(
            {
                **question_public(question),
                "user_answer": user_answer,
                "correct": correct if question.type != "essay" else None,
                "got_score": score,
            }
        )
    return ok(
        {
            "attempt_id": attempt.id,
            "title": paper.title if paper else "",
            "score": attempt.score,
            "passed": bool(attempt.passed),
            "items": items,
        }
    )
