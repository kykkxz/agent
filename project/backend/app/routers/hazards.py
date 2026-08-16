from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.hazard import Hazard, HazardLog
from app.models.user import User
from app.schemas.common import ok, paginate
from app.services.hazard_records import next_hazard_id
from app.services.notify import push_notification

router = APIRouter(prefix="/hazards", tags=["hazards"])


def parse_json(raw: str | None, default):
    try:
        return json.loads(raw) if raw else default
    except json.JSONDecodeError:
        return default


def iso(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def can_view(user: User, hazard: Hazard) -> bool:
    if user.role == "Admin":
        return True
    if user.role == "SafetyOfficer":
        return hazard.project == user.project or hazard.reporter_id == user.id or hazard.assignee_id == user.id
    return hazard.reporter_id == user.id or hazard.assignee_id == user.id


def user_brief(db: Session, user_id: str | None) -> dict | None:
    if not user_id:
        return None
    user = db.get(User, user_id)
    if not user:
        return None
    return {"id": user.id, "name": user.name}


def hazard_summary(db: Session, item: Hazard) -> dict:
    images = parse_json(item.images_json, [])
    reporter = user_brief(db, item.reporter_id)
    return {
        "hazard_id": item.id,
        "title": item.title,
        "level": item.level,
        "status": item.status,
        "category": item.category,
        "reporter_name": reporter["name"] if reporter else "",
        "project": item.project,
        "created_at": iso(item.created_at),
        "thumbnail_url": images[0] if images else None,
    }


def hazard_detail(db: Session, item: Hazard) -> dict:
    logs = db.scalars(select(HazardLog).where(HazardLog.hazard_id == item.id).order_by(HazardLog.id)).all()
    timeline = []
    for log in logs:
        operator = user_brief(db, log.operator_id)
        timeline.append(
            {
                "node": log.node,
                "operator": operator["name"] if operator else "",
                "time": iso(log.created_at),
                "note": log.note,
            }
        )
    return {
        "hazard_id": item.id,
        "title": item.title,
        "description": item.description,
        "level": item.level,
        "category": item.category,
        "location": item.location,
        "location_coords": item.location_coords,
        "project": item.project,
        "reporter": user_brief(db, item.reporter_id),
        "occurred_at": item.occurred_at,
        "created_at": iso(item.created_at),
        "status": item.status,
        "media": {
            "images": parse_json(item.images_json, []),
            "videos": parse_json(item.videos_json, []),
        },
        "timeline": timeline,
        "assignment": parse_json(item.assignment_json, None),
        "rectification": parse_json(item.rectification_json, None),
        "review": parse_json(item.review_json, None),
    }


def add_log(db: Session, hazard_id: str, node: str, operator_id: str, note: str) -> None:
    db.add(HazardLog(hazard_id=hazard_id, node=node, operator_id=operator_id, note=note))


def save_uploads(files: list[UploadFile] | None, folder: str) -> list[str]:
    if not files:
        return []
    dest = Path(settings.upload_dir) / folder
    dest.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    for file in files:
        if not file.filename:
            continue
        target = dest / file.filename
        target.write_bytes(file.file.read())
        urls.append(f"/api/v1/files/{folder}/{file.filename}")
    return urls


class AssignBody(BaseModel):
    assignee_id: str
    requirements: str
    deadline: str
    priority: str = "medium"


class ReviewBody(BaseModel):
    result: str
    comment: str = ""


class HazardJsonBody(BaseModel):
    title: str
    description: str
    level: str
    category: str
    location: str
    project: str
    occurred_at: str
    location_coords: str = ""


@router.get("")
def list_hazards(
    page: int = 1,
    page_size: int = 20,
    status: str = "",
    level: str = "",
    category: str = "",
    project: str = "",
    keyword: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Hazard)
    if user.role == "Employee":
        stmt = stmt.where(or_(Hazard.reporter_id == user.id, Hazard.assignee_id == user.id))
    elif user.role == "SafetyOfficer":
        stmt = stmt.where(
            or_(Hazard.project == user.project, Hazard.reporter_id == user.id, Hazard.assignee_id == user.id)
        )
    if status:
        stmt = stmt.where(Hazard.status.in_(status.split(",")))
    if level:
        stmt = stmt.where(Hazard.level.in_(level.split(",")))
    if category:
        stmt = stmt.where(Hazard.category == category)
    if project:
        stmt = stmt.where(Hazard.project == project)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Hazard.title.like(like), Hazard.id.like(like), Hazard.description.like(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Hazard.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ok(paginate([hazard_summary(db, item) for item in items], total, page, page_size))


@router.post("")
async def create_hazard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    level: str | None = Form(default=None),
    category: str | None = Form(default=None),
    location: str | None = Form(default=None),
    project: str | None = Form(default=None),
    occurred_at: str | None = Form(default=None),
    location_coords: str = Form(default=""),
    images: list[UploadFile] | None = File(default=None),
    body: HazardJsonBody | None = None,
):
    payload = body
    if title:
        payload = HazardJsonBody(
            title=title,
            description=description or "",
            level=level or "minor",
            category=category or "other",
            location=location or "",
            project=project or user.project,
            occurred_at=occurred_at or datetime.now().isoformat(),
            location_coords=location_coords,
        )
    if not payload:
        return JSONResponse({"code": 40001, "message": "参数校验失败", "data": None}, 400)
    if images and len(images) > 9:
        return JSONResponse({"code": 40002, "message": "图片数量超限（最多 9 张）", "data": None}, 400)
    hazard = Hazard(
        id=next_hazard_id(db),
        title=payload.title,
        description=payload.description,
        level=payload.level,
        category=payload.category,
        location=payload.location,
        location_coords=payload.location_coords,
        project=payload.project,
        occurred_at=payload.occurred_at,
        status="pending",
        reporter_id=user.id,
        images_json=json.dumps(save_uploads(images, "hazards"), ensure_ascii=False),
    )
    db.add(hazard)
    add_log(db, hazard.id, "上报", user.id, "隐患首次上报")
    officers = db.scalars(select(User).where(User.role.in_(["Admin", "SafetyOfficer"]), User.is_active.is_(True))).all()
    for officer in officers:
        push_notification(db, officer.id, "新隐患待派单", hazard.title, "hazard", hazard.id)
    db.commit()
    return ok({"hazard_id": hazard.id, "status": hazard.status, "created_at": iso(hazard.created_at)})


@router.get("/{hazard_id}")
def get_hazard(hazard_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hazard = db.get(Hazard, hazard_id)
    if not hazard:
        return JSONResponse({"code": 40401, "message": "隐患不存在", "data": None}, 404)
    if not can_view(user, hazard):
        return JSONResponse({"code": 40301, "message": "无权查看该隐患", "data": None}, 403)
    return ok(hazard_detail(db, hazard))


@router.post("/{hazard_id}/assign")
def assign_hazard(
    hazard_id: str,
    body: AssignBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "SafetyOfficer")),
):
    hazard = db.get(Hazard, hazard_id)
    if not hazard:
        return JSONResponse({"code": 40401, "message": "隐患不存在", "data": None}, 404)
    if hazard.status not in {"pending", "rejected"}:
        return JSONResponse({"code": 40004, "message": "隐患状态不允许当前操作", "data": None}, 400)
    try:
        deadline = datetime.fromisoformat(body.deadline.replace("Z", "+00:00"))
    except ValueError:
        return JSONResponse({"code": 40005, "message": "整改截止日期不合法", "data": None}, 400)
    now = datetime.now(deadline.tzinfo or UTC)
    if deadline < now:
        return JSONResponse({"code": 40005, "message": "整改截止日期不合法", "data": None}, 400)
    if hazard.level == "critical" and deadline - now > timedelta(days=7):
        return JSONResponse({"code": 40006, "message": "重大隐患整改期限不得超过 7 天", "data": None}, 400)
    assignee = db.get(User, body.assignee_id)
    if not assignee:
        return JSONResponse({"code": 40001, "message": "责任人不存在", "data": None}, 400)
    hazard.assignee_id = assignee.id
    hazard.status = "processing"
    hazard.assignment_json = json.dumps(
        {
            "assignee": {"id": assignee.id, "name": assignee.name},
            "requirements": body.requirements,
            "deadline": body.deadline,
            "priority": body.priority,
        },
        ensure_ascii=False,
    )
    add_log(db, hazard.id, "派单", user.id, f"指派{assignee.name}处理，截止{body.deadline}")
    push_notification(db, assignee.id, "隐患已派发", f"{hazard.title} 已指派给您整改", "hazard", hazard.id)
    db.commit()
    return ok({"hazard_id": hazard.id, "status": hazard.status, "assigned_at": iso(datetime.now(UTC))})


@router.post("/{hazard_id}/rectify")
async def rectify_hazard(
    hazard_id: str,
    measures: str = Form(...),
    completed_at: str = Form(default=""),
    images_after: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    hazard = db.get(Hazard, hazard_id)
    if not hazard:
        return JSONResponse({"code": 40401, "message": "隐患不存在", "data": None}, 404)
    if hazard.status != "processing":
        return JSONResponse({"code": 40007, "message": "隐患状态不允许提交整改", "data": None}, 400)
    if user.role == "Employee" and hazard.assignee_id != user.id:
        return JSONResponse({"code": 40302, "message": "非被指派人无权操作", "data": None}, 403)
    if len(measures.strip()) < 20:
        return JSONResponse({"code": 40008, "message": "整改描述不足 20 字", "data": None}, 400)
    saved = save_uploads(images_after, "rectify")
    hazard.status = "pending_review"
    hazard.rectification_json = json.dumps(
        {
            "measures": measures,
            "completed_at": completed_at or datetime.now().isoformat(),
            "images_after": saved,
        },
        ensure_ascii=False,
    )
    add_log(db, hazard.id, "整改", user.id, measures[:80])
    officers = db.scalars(select(User).where(User.role.in_(["Admin", "SafetyOfficer"]))).all()
    for officer in officers:
        push_notification(db, officer.id, "隐患待验收", hazard.title, "hazard", hazard.id)
    db.commit()
    return ok({"hazard_id": hazard.id, "status": hazard.status, "rectified_at": datetime.now().isoformat()})


@router.post("/{hazard_id}/review")
def review_hazard(
    hazard_id: str,
    body: ReviewBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "SafetyOfficer")),
):
    hazard = db.get(Hazard, hazard_id)
    if not hazard:
        return JSONResponse({"code": 40401, "message": "隐患不存在", "data": None}, 404)
    if hazard.status != "pending_review":
        return JSONResponse({"code": 40010, "message": "隐患状态不允许验收", "data": None}, 400)
    if body.result == "rejected" and len(body.comment.strip()) < 10:
        return JSONResponse({"code": 40011, "message": "驳回时必须填写原因（≥ 10 字）", "data": None}, 400)
    hazard.reviewer_id = user.id
    hazard.review_json = json.dumps({"result": body.result, "comment": body.comment}, ensure_ascii=False)
    if body.result == "approved":
        hazard.status = "closed"
        add_log(db, hazard.id, "验收", user.id, body.comment or "整改达标，闭环")
    else:
        hazard.status = "processing"
        add_log(db, hazard.id, "驳回", user.id, body.comment)
        if hazard.assignee_id:
            push_notification(db, hazard.assignee_id, "整改被驳回", body.comment, "hazard", hazard.id)
    db.commit()
    return ok({"hazard_id": hazard.id, "status": hazard.status})
class RectifyJsonBody(BaseModel):
    measures: str
    completed_at: str = ""


@router.post("/json")
def create_hazard_json(body: HazardJsonBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hazard = Hazard(
        id=next_hazard_id(db),
        title=body.title,
        description=body.description,
        level=body.level,
        category=body.category,
        location=body.location,
        location_coords=body.location_coords,
        project=body.project,
        occurred_at=body.occurred_at,
        status="pending",
        reporter_id=user.id,
    )
    db.add(hazard)
    add_log(db, hazard.id, "上报", user.id, "隐患首次上报")
    officers = db.scalars(select(User).where(User.role.in_(["Admin", "SafetyOfficer"]), User.is_active.is_(True))).all()
    for officer in officers:
        push_notification(db, officer.id, "新隐患待派单", hazard.title, "hazard", hazard.id)
    db.commit()
    return ok({"hazard_id": hazard.id, "status": hazard.status, "created_at": iso(hazard.created_at)})


@router.post("/{hazard_id}/rectify-json")
def rectify_hazard_json(
    hazard_id: str,
    body: RectifyJsonBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    hazard = db.get(Hazard, hazard_id)
    if not hazard:
        return JSONResponse({"code": 40401, "message": "隐患不存在", "data": None}, 404)
    if hazard.status != "processing":
        return JSONResponse({"code": 40007, "message": "隐患状态不允许提交整改", "data": None}, 400)
    if user.role == "Employee" and hazard.assignee_id != user.id:
        return JSONResponse({"code": 40302, "message": "非被指派人无权操作", "data": None}, 403)
    if len(body.measures.strip()) < 20:
        return JSONResponse({"code": 40008, "message": "整改描述不足 20 字", "data": None}, 400)
    hazard.status = "pending_review"
    hazard.rectification_json = json.dumps(
        {"measures": body.measures, "completed_at": body.completed_at or datetime.now().isoformat(), "images_after": []},
        ensure_ascii=False,
    )
    add_log(db, hazard.id, "整改", user.id, body.measures[:80])
    db.commit()
    return ok({"hazard_id": hazard.id, "status": hazard.status})
