from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hazard import Hazard, HazardLog
from app.models.user import User
from app.services.notify import push_notification

RISK_LEVELS = {"高": "critical", "中": "major", "低": "minor"}
RISK_ORDER = {"高": 3, "中": 2, "低": 1}
CATEGORY_KEYWORDS = (
    ("临边", "edge_protection"),
    ("护栏", "edge_protection"),
    ("安全带", "height_work"),
    ("高处", "height_work"),
    ("脚手架", "height_work"),
    ("用电", "temp_electricity"),
    ("电缆", "temp_electricity"),
    ("配电", "temp_electricity"),
    ("消防", "fire_safety"),
    ("灭火", "fire_safety"),
    ("机械", "machinery"),
    ("吊装", "machinery"),
)


def next_hazard_id(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"HD-{today}-"
    last = db.scalar(
        select(Hazard.id)
        .where(Hazard.id.like(f"{prefix}%"))
        .order_by(Hazard.id.desc())
    )
    seq = int(last.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


def _highest_risk(items: list[dict[str, Any]]) -> str:
    return max(
        (str(item.get("risk", "低")).strip() for item in items),
        key=lambda risk: RISK_ORDER.get(risk, 0),
        default="低",
    )


def _category(items: list[dict[str, Any]]) -> str:
    labels = " ".join(str(item.get("label", "")) for item in items)
    for keyword, category in CATEGORY_KEYWORDS:
        if keyword in labels:
            return category
    return "other"


def _description(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        label = str(item.get("label") or "现场隐患").strip()
        risk = str(item.get("risk") or "待定").strip()
        note = str(
            item.get("note")
            or item.get("description")
            or item.get("reason")
            or ""
        ).strip()
        fix = str(item.get("fix") or item.get("suggestion") or "").strip()
        detail = f"{index}. {label}（{risk}风险）"
        if note:
            detail += f"，位置：{note}"
        if fix:
            detail += f"；整改建议：{fix}"
        lines.append(detail)
    return "\n".join(lines)


def create_hazard_from_analysis(
    db: Session,
    user: User,
    analysis: dict[str, Any],
) -> dict[str, Any] | None:
    items = [item for item in analysis.get("items", []) if isinstance(item, dict)]
    if not items:
        return None

    highest_risk = _highest_risk(items)
    first_label = str(items[0].get("label") or "现场隐患").strip()
    title = (
        f"AI识别：{first_label}"
        if len(items) == 1
        else f"AI识别：{len(items)}项现场隐患"
    )
    first_location = str(items[0].get("note") or "现场图片识别").strip()
    if len(items) > 1 and first_location != "现场图片识别":
        first_location = f"{first_location}等{len(items)}处"
    images = list(
        dict.fromkeys(
            url
            for url in (analysis.get("original_url"), analysis.get("image_url"))
            if isinstance(url, str) and url
        )
    )

    hazard = Hazard(
        id=next_hazard_id(db),
        title=title,
        description=_description(items),
        level=RISK_LEVELS.get(highest_risk, "minor"),
        category=_category(items),
        location=first_location[:255],
        project=user.project,
        occurred_at=datetime.now(UTC).isoformat(),
        status="pending",
        reporter_id=user.id,
        images_json=json.dumps(images, ensure_ascii=False),
    )
    db.add(hazard)
    db.add(
        HazardLog(
            hazard_id=hazard.id,
            node="AI识别上报",
            operator_id=user.id,
            note=f"图片分析任务 {analysis.get('job_id', '')} 自动创建",
        )
    )
    officers = db.scalars(
        select(User).where(
            User.role.in_(["Admin", "SafetyOfficer"]),
            User.is_active.is_(True),
        )
    ).all()
    for officer in officers:
        push_notification(
            db,
            officer.id,
            "AI识别隐患待派单",
            hazard.title,
            "hazard",
            hazard.id,
        )
    db.commit()
    return {
        "hazard_id": hazard.id,
        "title": hazard.title,
        "level": hazard.level,
        "status": hazard.status,
    }
