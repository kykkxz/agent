from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.chat import ChatMessage
from app.models.exam import ExamAttempt
from app.models.hazard import Hazard
from app.models.user import User
from app.schemas.common import ok

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/hazards/overview")
def hazard_overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = db.scalars(select(Hazard)).all()
    status = Counter(item.status for item in items)
    level = Counter(item.level for item in items)
    closed = status.get("closed", 0)
    total = len(items)
    return ok(
        {
            "total": total,
            "closed": closed,
            "closure_rate": round(closed / total * 100, 1) if total else 0,
            "by_status": dict(status),
            "by_level": dict(level),
            "by_category": dict(Counter(item.category for item in items)),
            "by_project": dict(Counter(item.project for item in items)),
        }
    )


@router.get("/hazards/trend")
def hazard_trend(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = db.scalars(select(Hazard)).all()
    buckets: dict[str, int] = {}
    for item in items:
        key = item.created_at.strftime("%Y-%m-%d") if item.created_at else "unknown"
        buckets[key] = buckets.get(key, 0) + 1
    return ok([{"date": key, "count": value} for key, value in sorted(buckets.items())])


@router.get("/exams/overview")
def exam_overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    attempts = db.scalars(select(ExamAttempt).where(ExamAttempt.status == "submitted")).all()
    scores = [item.score or 0 for item in attempts]
    return ok(
        {
            "attempts": len(attempts),
            "pass_count": sum(1 for item in attempts if item.passed),
            "pass_rate": round(sum(1 for item in attempts if item.passed) / len(attempts) * 100, 1) if attempts else 0,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        }
    )


@router.get("/ai-satisfaction")
def ai_satisfaction(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    messages = db.scalars(select(ChatMessage).where(ChatMessage.role == "assistant")).all()
    up = sum(1 for item in messages if item.feedback == "up")
    down = sum(1 for item in messages if item.feedback == "down")
    return ok({"total": len(messages), "up": up, "down": down, "satisfaction": round(up / (up + down) * 100, 1) if up + down else 0})