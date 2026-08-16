from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ok
from app.services.hazard_records import create_hazard_from_analysis
from app.services.hazard_vision import analyze_hazard_image
from sqlalchemy.orm import Session

router = APIRouter(prefix="/hazard-analysis", tags=["hazard-analysis"])
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024


@router.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    prompt: str = Form("识别图中全部施工安全隐患，按风险等级标注并给出处置建议。"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        return JSONResponse({"code": 40001, "message": "仅支持 JPG、PNG、WEBP 图片", "data": None}, 400)
    content = await image.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        return JSONResponse({"code": 40002, "message": "图片不能超过 15MB", "data": None}, 413)
    try:
        result = analyze_hazard_image(content, suffix, prompt)
        result["created_hazard"] = create_hazard_from_analysis(db, user, result)
        return ok(result)
    except ValueError as exc:
        return JSONResponse({"code": 40001, "message": str(exc), "data": None}, 400)
    except RuntimeError as exc:
        return JSONResponse({"code": 40203, "message": str(exc), "data": None}, 503)
