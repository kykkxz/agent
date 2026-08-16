from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models.user import User
from app.routers.auth import user_payload
from app.schemas.common import ok, paginate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


class UserBody(BaseModel):
    username: str
    name: str
    password: str | None = None
    role: str = "Employee"
    department: str = ""
    project: str = ""
    phone: str = ""
    is_active: bool = True


def next_user_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(User)) or 0
    return f"U{count + 1:03d}"


@router.get("")
def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    role: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    stmt = select(User)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(User.username.like(like) | User.name.like(like))
    if role:
        stmt = stmt.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)).all()
    return ok(paginate([user_payload(item) | {"is_active": item.is_active} for item in items], total, page, page_size))


@router.post("")
def create_user(body: UserBody, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin"))):
    exists = db.scalar(select(User).where(User.username == body.username))
    if exists:
        return JSONResponse({"code": 40001, "message": "用户名已存在", "data": None}, 409)
    user = User(
        id=next_user_id(db),
        username=body.username,
        name=body.name,
        password_hash=hash_password(body.password or "User@123456"),
        role=body.role,
        department=body.department,
        project=body.project,
        phone=body.phone,
        is_active=body.is_active,
    )
    db.add(user)
    db.commit()
    return ok(user_payload(user))


@router.put("/{user_id}")
def update_user(user_id: str, body: UserBody, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin"))):
    user = db.get(User, user_id)
    if not user:
        return JSONResponse({"code": 40400, "message": "用户不存在", "data": None}, 404)
    user.name = body.name
    user.role = body.role
    user.department = body.department
    user.project = body.project
    user.phone = body.phone
    user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)
    db.commit()
    return ok(user_payload(user))


@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), current: User = Depends(require_roles("Admin"))):
    user = db.get(User, user_id)
    if not user:
        return JSONResponse({"code": 40400, "message": "用户不存在", "data": None}, 404)
    if user.id == current.id:
        return JSONResponse({"code": 40001, "message": "不能删除当前登录账号", "data": None}, 400)
    user.is_active = False
    db.commit()
    return ok(None, "已停用")


@router.get("/options")
def user_options(db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "SafetyOfficer"))):
    users = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.name)).all()
    return ok([{"id": item.id, "name": item.name, "role": item.role, "project": item.project} for item in users])