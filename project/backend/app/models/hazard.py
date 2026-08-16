from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Hazard(Base):
    __tablename__ = "hazards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(255))
    location_coords: Mapped[str] = mapped_column(String(64), default="")
    project: Mapped[str] = mapped_column(String(128), index=True)
    occurred_at: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    images_json: Mapped[str] = mapped_column(Text, default="[]")
    videos_json: Mapped[str] = mapped_column(Text, default="[]")
    assignment_json: Mapped[str] = mapped_column(Text, default="null")
    rectification_json: Mapped[str] = mapped_column(Text, default="null")
    review_json: Mapped[str] = mapped_column(Text, default="null")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HazardLog(Base):
    __tablename__ = "hazard_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hazard_id: Mapped[str] = mapped_column(ForeignKey("hazards.id"), index=True)
    node: Mapped[str] = mapped_column(String(32))
    operator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())