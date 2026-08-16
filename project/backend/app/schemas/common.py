from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None
    timestamp: int = Field(default_factory=lambda: int(__import__("time").time()))


class PageData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    import time

    return {
        "code": 0,
        "message": message,
        "data": data,
        "timestamp": int(time.time()),
    }


def fail(code: int, message: str, http_status: int = 400) -> tuple[dict[str, Any], int]:
    import time

    return (
        {
            "code": code,
            "message": message,
            "data": None,
            "timestamp": int(time.time()),
        },
        http_status,
    )


def paginate(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }