from flask import Blueprint, request

from app.core.database import get_db
from app.core.dependencies import role_required
from app.core.response import BizException, success
from app.models import OperationLog
from app.services.common import iso, paginate

bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")


def _int_arg(name: str, default: int | None = None) -> int | None:
    value = request.args.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise BizException(1001, f"{name} 必须为整数", 400) from error


@bp.get("")
@role_required("admin")
def list_logs():
    query = get_db().query(OperationLog)
    user_id = _int_arg("user_id")
    action = request.args.get("action")
    if user_id is not None:
        query = query.filter(OperationLog.user_id == user_id)
    if action:
        query = query.filter(OperationLog.action == action)
    return success(
        paginate(
            query.order_by(OperationLog.created_at.desc()),
            _int_arg("page", 1) or 1,
            _int_arg("per_page", 50) or 50,
            lambda item: {
                "id": item.id,
                "user_id": item.user_id,
                "action": item.action,
                "details": item.details,
                "created_at": iso(item.created_at),
            },
        )
    )
