from flask import Blueprint, g, request

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import login_required
from app.core.response import BizException, success
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import (
    CredentialsRequest,
    UpdatePasswordRequest,
    UpdateProfileRequest,
    validate_request,
)

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _auth_data(user: User) -> dict:
    return {
        "access_token": create_access_token(user.username),
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


@bp.post("/login")
def login():
    payload = validate_request(CredentialsRequest, request.get_json(silent=True))
    user = User.find_by_username(get_db(), payload.username) # type: ignore[reportAttributeAccessIssue]
    if user is None or not verify_password(payload.password, user.password_hash): # type: ignore[reportAttributeAccessIssue]
        raise BizException(1002, "用户名或密码错误", 401)
    return success(_auth_data(user))


@bp.post("/register")
def register():
    payload = validate_request(CredentialsRequest, request.get_json(silent=True))
    session = get_db()
    if User.find_by_username(session, payload.username) is not None: # type: ignore[reportAttributeAccessIssue]
        raise BizException(1004, "用户名已存在", 400)
    user = User(
        username=payload.username, password_hash=hash_password(payload.password), role="user" # type: ignore[reportAttributeAccessIssue]
    )
    session.add(user)
    session.commit()
    return success(_auth_data(user))


@bp.get("/me")
@login_required
def me():
    user = g.current_user
    return success({"id": user.id, "username": user.username, "role": user.role})


@bp.post("/logout")
@login_required
def logout():
    return success(message="已登出")

@bp.put("/profile")
@login_required
def profile():
    user = g.current_user
    payload = validate_request(UpdateProfileRequest, request.get_json(silent=True))
    session = get_db()
    existing_user = User.find_by_username(session, payload.username) # type: ignore[reportAttributeAccessIssue]
    if existing_user is not None and existing_user.id != user.id:
        raise BizException(1004, "用户名已存在", 400)

    user.update_profile(payload.username)# type: ignore[reportAttributeAccessIssue]
    session.commit()
    return success(_auth_data(user), "用户名更新成功")


@bp.put("/password")
@login_required
def password():
    user = g.current_user
    payload = validate_request(UpdatePasswordRequest, request.get_json(silent=True))
    if not verify_password(payload.old_password, user.password_hash): # type: ignore[reportAttributeAccessIssue]
        raise BizException(1002, "原密码错误", 400)

    user.update_password(hash_password(payload.new_password)) # type: ignore[reportAttributeAccessIssue]
    get_db().commit()
    return success(message="密码更新成功")
