from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import ok
from app.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class PasswordBody(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "department": user.department,
        "project": user.project,
        "phone": user.phone,
    }


def token_payload(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "expires_in": 7200,
        "user": user_payload(user),
    }


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        return JSONResponse({"code": 40101, "message": "用户名或密码错误", "data": None}, 401)
    if not user.is_active:
        return JSONResponse({"code": 40102, "message": "账户已被禁用", "data": None}, 401)
    return ok(token_payload(user))


@router.post("/refresh")
def refresh(body: RefreshBody, db: Session = Depends(get_db)):
    user_id = decode_token(body.refresh_token, "refresh")
    if not user_id:
        return JSONResponse({"code": 40103, "message": "refresh_token 无效或已过期", "data": None}, 401)
    user = db.get(User, user_id)
    if not user:
        return JSONResponse({"code": 40103, "message": "refresh_token 无效或已过期", "data": None}, 401)
    return ok(token_payload(user))


@router.post("/logout")
def logout(_: User = Depends(get_current_user)):
    return ok(None, "已退出登录")


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok(user_payload(user))


@router.put("/password")
def change_password(body: PasswordBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(body.old_password, user.password_hash):
        return JSONResponse({"code": 40104, "message": "旧密码错误", "data": None}, 400)
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return ok(None, "密码修改成功")