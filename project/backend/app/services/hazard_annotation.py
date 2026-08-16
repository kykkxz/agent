"""施工安全隐患识别结果的解析、坐标转换与图片批注。"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path

import cv2
import numpy as np
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

RISK_COLOR = {
    "高": (0, 0, 255),
    "中": (0, 165, 255),
    "低": (0, 255, 255),
}

FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simsun.ttc"),
)


def load_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"文件为空: {path}")
    return text


def encode_image_data_url(image_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(image_path))
    if mime is None:
        ext = image_path.suffix.lower()
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".gif": "image/gif",
        }.get(ext, "application/octet-stream")
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def extract_json_array(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "hazards", "results", "data", "annotations"):
                if isinstance(data.get(key), list):
                    return data[key]
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, list):
            return data

    raise ValueError(f"无法从模型输出中解析 JSON 数组:\n{text[:800]}")


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def to_pixel_bbox(item: dict, width: int, height: int) -> tuple[int, int, int, int] | None:
    bbox_px = item.get("bbox_px")
    if isinstance(bbox_px, (list, tuple)) and len(bbox_px) == 4 and all(
        isinstance(v, (int, float)) for v in bbox_px
    ):
        x1, y1, x2, y2 = [int(round(float(v))) for v in bbox_px]
    else:
        bbox_norm = item.get("bbox_norm")
        if not (isinstance(bbox_norm, (list, tuple)) and len(bbox_norm) == 4):
            return None
        nx1, ny1, nx2, ny2 = [clamp01(v) for v in bbox_norm]
        x1 = int(round(nx1 * width))
        y1 = int(round(ny1 * height))
        x2 = int(round(nx2 * width))
        y2 = int(round(ny2 * height))

    x1 = max(0, min(width - 1, x1))
    x2 = max(0, min(width - 1, x2))
    y1 = max(0, min(height - 1, y1))
    y2 = max(0, min(height - 1, y2))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    return x1, y1, x2, y2


def resolve_color(item: dict) -> tuple[int, int, int]:
    color = item.get("color_bgr")
    if isinstance(color, (list, tuple)) and len(color) == 3:
        try:
            return tuple(int(v) for v in color)  # type: ignore[return-value]
        except (TypeError, ValueError):
            pass
    risk = str(item.get("risk", "")).strip()
    return RISK_COLOR.get(risk, (0, 255, 255))


def load_cjk_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    raise RuntimeError("未找到可用中文字体，请安装 simhei.ttf 或微软雅黑字体。")


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """按像素宽度逐字换行，避免中文标注越出标签框。"""
    lines: list[str] = []
    line = ""
    for char in text:
        candidate = line + char
        left, _, right, _ = draw.textbbox((0, 0), candidate, font=font)
        if line and right - left > max_width:
            lines.append(line)
            line = char
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines or ["隐患"]


def label_text(item: dict) -> str:
    item_id = item.get("id", "")
    prefix = f"#{item_id} " if item_id != "" else ""
    label = str(item.get("label", "隐患")).strip() or "隐患"
    risk = str(item.get("risk", "")).strip()
    return f"{prefix}{label}" + (f"\n风险等级：{risk}" if risk else "")


def label_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_text_width: int,
    padding: int,
    line_gap: int,
) -> tuple[list[str], int, int]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        lines.extend(wrap_text(draw, paragraph, font, max_text_width))
    widths = [draw.textbbox((0, 0), line, font=font)[2] for line in lines]
    line_height = draw.textbbox((0, 0), "安全", font=font)[3]
    return lines, max(widths) + padding * 2, line_height * len(lines) + line_gap * (len(lines) - 1) + padding * 2


def place_callouts(
    entries: list[dict],
    width: int,
    height: int,
    gap: int,
) -> None:
    """将标签分到目标左右两侧，同侧按垂直顺序避让。"""
    for side in ("left", "right"):
        group = [entry for entry in entries if entry["side"] == side]
        group.sort(key=lambda entry: entry["target"][1])
        previous_bottom = gap
        for entry in group:
            box_w, box_h = entry["label_size"]
            target_x, target_y = entry["target"]
            desired_y = int(target_y - box_h / 2)
            y = max(gap, desired_y, previous_bottom + gap)
            entry["xy"] = (entry["x"], y)
            previous_bottom = y + box_h

        # The forward pass can exceed the image. Shift the full side back while
        # retaining label-to-label spacing.
        if group and previous_bottom > height - gap:
            shift = previous_bottom - (height - gap)
            for entry in group:
                x, y = entry["xy"]
                entry["xy"] = (x, y - shift)
            if group[0]["xy"][1] < gap:
                overflow = gap - group[0]["xy"][1]
                for entry in group:
                    x, y = entry["xy"]
                    entry["xy"] = (x, y + overflow)


def annotate_image(image: np.ndarray, items: list) -> tuple[np.ndarray, list]:
    out = image.copy()
    h, w = out.shape[:2]
    thickness = max(2, int(round(min(h, w) / 400)))
    font_size = max(17, int(round(min(h, w) / 45)))
    padding = max(8, font_size // 2)
    line_gap = max(3, font_size // 5)
    margin = max(12, min(h, w) // 45)
    max_text_width = max(135, min(w // 4, int(w * 0.23)))
    drawn: list = []
    callouts: list[dict] = []

    # OpenCV draws the target boxes; Pillow handles Chinese text and the
    # rounded callout plates without relying on an OpenCV font that lacks CJK.
    pil_out = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_out)
    font = load_cjk_font(font_size)

    for item in items:
        if not isinstance(item, dict):
            continue
        box = to_pixel_bbox(item, w, h)
        if box is None:
            continue
        x1, y1, x2, y2 = box
        color = resolve_color(item)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)
        text = label_text(item)
        lines, label_w, label_h = label_size(
            draw, text, font, max_text_width, padding, line_gap
        )
        center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
        side = "right" if center_x >= w // 2 else "left"
        x = min(w - label_w - margin, x2 + margin) if side == "right" else max(margin, x1 - label_w - margin)
        callouts.append(
            {
                "target": (center_x, center_y),
                "side": side,
                "x": x,
                "label_size": (label_w, label_h),
                "lines": lines,
                "color": tuple(reversed(color)),
            }
        )

        drawn.append(
            {
                **item,
                "bbox_px": [x1, y1, x2, y2],
                "bbox_norm": [
                    round(x1 / w, 6),
                    round(y1 / h, 6),
                    round(x2 / w, 6),
                    round(y2 / h, 6),
                ],
            }
        )

    # Rebuild the Pillow backing image after OpenCV has completed box drawing.
    pil_out = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_out)
    place_callouts(callouts, w, h, margin)
    for callout in callouts:
        x, y = callout["xy"]
        label_w, label_h = callout["label_size"]
        color_rgb = callout["color"]
        target_x, target_y = callout["target"]
        on_right = callout["side"] == "right"
        anchor = (x, y + label_h // 2) if on_right else (x + label_w, y + label_h // 2)

        draw.line((target_x, target_y, anchor[0], anchor[1]), fill=color_rgb, width=thickness)
        arrow = max(7, thickness * 4)
        direction = 1 if on_right else -1
        draw.polygon(
            [(target_x, target_y), (target_x + direction * arrow, target_y - arrow // 2), (target_x + direction * arrow, target_y + arrow // 2)],
            fill=color_rgb,
        )
        draw.rounded_rectangle(
            (x, y, x + label_w, y + label_h),
            radius=max(6, padding // 2),
            fill=(255, 255, 255),
            outline=color_rgb,
            width=thickness,
        )
        cursor_y = y + padding
        for line in callout["lines"]:
            left, _, right, bottom = draw.textbbox((0, 0), line, font=font)
            text_x = x + (label_w - (right - left)) // 2
            draw.text((text_x, cursor_y), line, font=font, fill=color_rgb)
            cursor_y += bottom + line_gap

    return cv2.cvtColor(np.asarray(pil_out), cv2.COLOR_RGB2BGR), drawn


def call_vision_api(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    image_path: Path,
) -> str:
    h, w = cv2.imread(str(image_path), cv2.IMREAD_COLOR).shape[:2]
    size_hint = f"原图像素尺寸: width={w}, height={h}。请据此填写 bbox_px 与 bbox_norm。"
    content_text = user_prompt.strip()
    if content_text:
        content_text = f"{content_text}\n\n{size_hint}"
    else:
        content_text = size_hint

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": content_text},
                {
                    "type": "image_url",
                    "image_url": {"url": encode_image_data_url(image_path)},
                },
            ],
        },
    ]

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("模型返回空内容")
    return content

