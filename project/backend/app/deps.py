from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security import decode_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": 40100, "message": "未认证"})
    user_id = decode_token(authorization.removeprefix("Bearer ").strip(), "access")
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": 40100, "message": "Token 无效或已过期"})
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": 40102, "message": "账户不可用"})
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail={"code": 40303, "message": "角色无此功能权限"})
        return user

    return checker