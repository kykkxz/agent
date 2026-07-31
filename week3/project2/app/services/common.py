from collections.abc import Iterable
from math import ceil
from typing import Any

from sqlalchemy.orm import Query

from app.models import Customer, EmailRecord, Experiment, OperationLog, User


def paginate(query: Query[Any], page: int, per_page: int, serializer) -> dict[str, Any]:
    page = max(page, 1)
    per_page = min(max(per_page, 1), 100)
    total = query.count()
    return {
        "items": [serializer(item) for item in query.offset((page - 1) * per_page).limit(per_page)],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": ceil(total / per_page) if total else 0,
    }


def iso(value: object | None) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def customer_out(customer: Customer) -> dict[str, Any]:
    return {
        "id": customer.id,
        "gender": customer.gender,
        "age": customer.age,
        "driving_license": customer.driving_license,
        "region_code": customer.region_code,
        "previously_insured": customer.previously_insured,
        "vehicle_age": customer.vehicle_age,
        "vehicle_damage": customer.vehicle_damage,
        "annual_premium": customer.annual_premium,
        "policy_sales_channel": customer.policy_sales_channel,
        "vintage": customer.vintage,
        "response": customer.response,
        "predicted_prob": customer.predicted_prob,
    }


def experiment_out(experiment: Experiment) -> dict[str, Any]:
    return {
        "id": experiment.id,
        "model_name": experiment.model_name,
        "accuracy": experiment.accuracy,
        "precision": experiment.precision,
        "recall": experiment.recall,
        "f1_score": experiment.f1_score,
        "roc_auc": experiment.roc_auc,
        "params": experiment.params,
        "model_path": experiment.model_path,
        "is_best": experiment.is_best,
        "created_at": iso(experiment.created_at),
    }


def email_out(record: EmailRecord, include_content: bool = False) -> dict[str, Any]:
    data = {
        "id": record.id,
        "customer_id": record.customer_id,
        "subject": record.subject,
        "status": record.status,
        "created_at": iso(record.created_at),
    }
    if include_content:
        data["content"] = record.content
    return data


def log_operation(session, user_id: int, action: str, details: str) -> None:
    session.add(OperationLog(user_id=user_id, action=action, details=details))


def ensure_owned(record: EmailRecord | None, user: User) -> EmailRecord:
    from app.core.response import BizException

    if record is None:
        raise BizException(2001, "资源不存在", 404)
    if user.role != "admin" and record.created_by != user.id:
        raise BizException(2001, "资源不存在", 404)
    return record


def ids(values: Iterable[object]) -> list[int]:
    return [int(value) for value in values]
