from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import ok, paginate
from app.services.knowledge import kb_overview, list_documents, search_knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/overview")
def overview(_: User = Depends(get_current_user)):
    return ok(kb_overview())


@router.get("/documents")
def documents(page: int = 1, page_size: int = 20, keyword: str = "", type: str = "", _: User = Depends(get_current_user)):
    items, total = list_documents(keyword=keyword, doc_type=type, page=page, page_size=page_size)
    return ok(paginate(items, total, page, page_size))


@router.get("/search")
def search(q: str, limit: int = 8, _: User = Depends(get_current_user)):
    return ok(search_knowledge(q, limit=limit))