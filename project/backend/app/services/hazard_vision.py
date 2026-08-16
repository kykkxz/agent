from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import cv2
from openai import OpenAI

from app.config import DEFAULT_HAZARD_PROMPT, settings
from app.services.hazard_annotation import (
    annotate_image,
    call_vision_api,
    extract_json_array,
    load_text,
)


def analyze_hazard_image(image_bytes: bytes, suffix: str, prompt: str) -> dict[str, Any]:
    if not settings.resolved_vision_api_key or not settings.resolved_vision_base_url:
        raise RuntimeError("尚未在 .env 配置视觉模型 API，无法执行图片识别")

    job_id = uuid.uuid4().hex
    job_dir = Path(settings.upload_dir) / "hazard-analysis" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_path = job_dir / f"original{suffix.lower()}"
    input_path.write_bytes(image_bytes)

    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("无法读取上传的图片")
    system_prompt = load_text(DEFAULT_HAZARD_PROMPT)
    client = OpenAI(
        api_key=settings.resolved_vision_api_key,
        base_url=settings.resolved_vision_base_url,
        timeout=settings.ai_request_timeout_seconds,
    )
    try:
        raw = call_vision_api(
            client, settings.resolved_vision_model, system_prompt, prompt, input_path
        )
    except Exception as exc:
        raise RuntimeError("视觉模型调用失败，请检查 .env 配置和模型能力") from exc
    items = extract_json_array(raw)
    annotated, drawn = annotate_image(image, items)
    output_path = job_dir / "annotated.png"
    if not cv2.imwrite(str(output_path), annotated):
        raise RuntimeError("批注图写入失败")
    (job_dir / "annotations.json").write_text(
        json.dumps({"items": drawn}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "job_id": job_id,
        "image_url": f"/api/v1/files/hazard-analysis/{job_id}/annotated.png",
        "original_url": f"/api/v1/files/hazard-analysis/{job_id}/{input_path.name}",
        "count": len(drawn),
        "items": drawn,
        "model": settings.resolved_vision_model,
    }
