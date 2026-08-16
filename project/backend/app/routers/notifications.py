from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import ok, paginate

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Notification).where(Notification.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Notification.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ok(
        paginate(
            [
                {
                    "id": item.id,
                    "title": item.title,
                    "content": item.content,
                    "type": item.type,
                    "related_id": item.related_id,
                    "is_read": bool(item.is_read),
                    "created_at": item.created_at.isoformat() if item.created_at else "",
                }
                for item in items
            ],
            total,
            page,
            page_size,
        )
    )


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id, Notification.is_read == 0
        )
    )
    return ok({"count": count or 0})


@router.put("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Notification, notification_id)
    if item and item.user_id == user.id:
        item.is_read = 1
        db.commit()
    return ok(None)


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.is_read == 0)).all()
    for item in items:
        item.is_read = 1
    db.commit()
    return ok(None)