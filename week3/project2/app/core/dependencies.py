from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import g, request

from app.core.database import get_db
from app.core.response import BizException
from app.core.security import decode_access_token
from app.models import User


def _authenticate() -> User:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise BizException(1002, "未授权", 401)
    user = get_db().query(User).filter_by(username=decode_access_token(authorization[7:])).first()
    if user is None:
        raise BizException(1002, "未授权", 401)
    g.current_user = user
    return user


def login_required(function: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any):
        _authenticate()
        return function(*args, **kwargs)

    return wrapper


def role_required(role: str):
    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any):
            user = _authenticate()
            if user.role != role:
                raise BizException(1003, "权限不足", 403)
            return function(*args, **kwargs)

        return wrapper

    return decorator
