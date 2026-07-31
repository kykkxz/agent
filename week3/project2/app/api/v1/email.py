from flask import Blueprint, g, request

from app.core.database import get_db
from app.core.dependencies import login_required
from app.core.response import BizException, success
from app.models import EmailRecord, User
from app.schemas import (
    BatchDeleteRequest,
    EmailStatusRequest,
    EmailUpdateRequest,
    GenerateEmailRequest,
    PromptUpdateRequest,
    validate_request,
)
from app.services.common import email_out, ensure_owned, log_operation, paginate
from app.services.email_service import EmailService

bp = Blueprint("email", __name__, url_prefix="/api/v1/email")
service = EmailService()


def _int_arg(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except ValueError as error:
        raise BizException(1001, f"{name} 必须为整数", 400) from error


@bp.get("/targets")
@login_required
def targets():
    try:
        percentile = float(request.args.get("percentile", 0.9))
    except ValueError as error:
        raise BizException(1001, "percentile 必须为数字", 400) from error
    page, per_page = _int_arg("page", 1), min(max(_int_arg("per_page", 20), 1), 100)
    return success(service.targets(get_db(), percentile, max(page, 1), per_page))


@bp.post("/generate")
@login_required
def generate():
    payload = validate_request(GenerateEmailRequest, request.get_json(silent=True))
    session = get_db()
    result = service.generate(session, g.current_user, payload.customer_ids, payload.limit)
    log_operation(
        session,
        g.current_user.id,
        "email_generation",
        f"generated={result['generated_count']}; failed={result['failed_count']}",
    )
    session.commit()
    return success(result)


@bp.get("/prompt")
@login_required
def get_prompt():
    template = service.active_template(get_db())
    return success({"name": template.name, "content": template.content})


@bp.put("/prompt")
@login_required
def update_prompt():
    payload = validate_request(PromptUpdateRequest, request.get_json(silent=True))
    placeholders = {
        "{gender}",
        "{age}",
        "{driving_license}",
        "{vehicle_age}",
        "{vehicle_damage}",
        "{annual_premium}",
    }
    if not placeholders.issubset(payload.content):
        raise BizException(1001, "Prompt 缺少客户画像占位符", 400)
    session = get_db()
    template = service.active_template(session)
    template.content = payload.content
    session.commit()
    return success({"name": template.name, "content": template.content})


@bp.get("/records")
@login_required
def records():
    session = get_db()
    user = g.current_user
    query = session.query(EmailRecord)
    status = request.args.get("status")
    if user.role != "admin":
        query = query.filter(EmailRecord.created_by == user.id)
    if status:
        query = query.filter(EmailRecord.status == status)

    def serialize(record: EmailRecord) -> dict:
        item = email_out(record)
        if user.role == "admin":
            creator = session.get(User, record.created_by)
            item["created_by_username"] = creator.username if creator else None
        return item

    return success(
        paginate(
            query.order_by(EmailRecord.created_at.desc()),
            _int_arg("page", 1),
            _int_arg("per_page", 50),
            serialize,
        )
    )


@bp.get("/records/<int:record_id>")
@login_required
def record_detail(record_id: int):
    record = ensure_owned(get_db().get(EmailRecord, record_id), g.current_user)
    return success(email_out(record, include_content=True))


@bp.put("/records/<int:record_id>")
@login_required
def update_record(record_id: int):
    payload = validate_request(EmailUpdateRequest, request.get_json(silent=True))
    if payload.email_subject is None and payload.email_content is None:
        raise BizException(1001, "至少提供一个更新字段", 400)
    session = get_db()
    record = ensure_owned(session.get(EmailRecord, record_id), g.current_user)
    if payload.email_subject is not None:
        record.subject = payload.email_subject
    if payload.email_content is not None:
        record.content = payload.email_content
    log_operation(session, g.current_user.id, "email_update", f"record_id={record_id}")
    session.commit()
    return success(email_out(record, include_content=True))


@bp.patch("/records/<int:record_id>")
@login_required
def mark_record(record_id: int):
    payload = validate_request(EmailStatusRequest, request.get_json(silent=True))
    session = get_db()
    record = ensure_owned(session.get(EmailRecord, record_id), g.current_user)
    record.status = payload.status
    log_operation(
        session, g.current_user.id, "email_mark", f"record_id={record_id}; status={payload.status}"
    )
    session.commit()
    return success(email_out(record, include_content=True))


@bp.delete("/records/<int:record_id>")
@login_required
def delete_record(record_id: int):
    session = get_db()
    record = ensure_owned(session.get(EmailRecord, record_id), g.current_user)
    session.delete(record)
    log_operation(session, g.current_user.id, "email_delete", f"record_id={record_id}")
    session.commit()
    return success({"success": True})


@bp.delete("/records")
@login_required
def batch_delete_records():
    payload = validate_request(BatchDeleteRequest, request.get_json(silent=True))
    session = get_db()
    records = session.query(EmailRecord).filter(EmailRecord.id.in_(payload.record_ids)).all()
    for record in records:
        ensure_owned(record, g.current_user)
    for record in records:
        session.delete(record)
    log_operation(session, g.current_user.id, "email_delete", f"record_ids={payload.record_ids}")
    session.commit()
    return success({"deleted_count": len(records)})
