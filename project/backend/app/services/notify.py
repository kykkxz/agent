from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.notification import Notification


def push_notification(
    db: Session,
    user_id: str,
    title: str,
    content: str,
    ntype: str = "system",
    related_id: str = "",
) -> Notification:
    item = Notification(
        user_id=user_id,
        title=title,
        content=content,
        type=ntype,
        related_id=related_id,
    )
    db.add(item)
    db.flush()
    return item