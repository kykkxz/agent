#!/usr/bin/env python
"""施工安全隐患图片批注命令行入口。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
from dotenv import load_dotenv
from openai import OpenAI

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import DEFAULT_HAZARD_PROMPT, PROJECT_ROOT  # noqa: E402
from app.services.hazard_annotation import (  # noqa: E402
    annotate_image,
    call_vision_api,
    extract_json_array,
    load_text,
)

DEFAULT_ENV = PROJECT_ROOT / ".env"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="传入提示词与图像，调用多模态模型识别隐患并输出批注图。"
    )
    parser.add_argument("-i", "--image", required=True, help="输入图像路径")
    parser.add_argument(
        "-p",
        "--prompt",
        default="请按系统要求识别并列出图中全部安全隐患。",
        help="附加到系统提示词后的用户提示词",
    )
    parser.add_argument("-o", "--output", help="批注图输出路径")
    parser.add_argument("--json-out", help="解析后的标注 JSON 输出路径")
    parser.add_argument("--raw-out", help="模型原始文本输出路径")
    parser.add_argument("--env", default=str(DEFAULT_ENV), help=".env 路径")
    parser.add_argument(
        "--system-prompt",
        default=str(DEFAULT_HAZARD_PROMPT),
        help="系统提示词文件路径",
    )
    parser.add_argument("--model", help="覆盖 .env 中的视觉模型名称")
    parser.add_argument(
        "--annotations",
        help="已有标注 JSON 路径；指定后跳过视觉 API 调用",
    )
    return parser


def load_cached_annotations(path: Path) -> tuple[list, str]:
    cached = json.loads(path.read_text(encoding="utf-8"))
    items = cached.get("items") if isinstance(cached, dict) else cached
    if not isinstance(items, list):
        raise ValueError("标注 JSON 中未找到 items 数组")
    model = (
        str(cached.get("model", "cached annotations"))
        if isinstance(cached, dict)
        else "cached annotations"
    )
    return items, model


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    image_path = Path(args.image).expanduser().resolve()
    if not image_path.is_file():
        print(f"错误: 图像不存在: {image_path}", file=sys.stderr)
        return 1

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        print(f"错误: OpenCV 无法读取图像: {image_path}", file=sys.stderr)
        return 1

    if args.annotations:
        annotations_path = Path(args.annotations).expanduser().resolve()
        if not annotations_path.is_file():
            print(f"错误: 标注 JSON 不存在: {annotations_path}", file=sys.stderr)
            return 1
        try:
            items, model = load_cached_annotations(annotations_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1
        print(f"使用已有标注: {annotations_path}")
    else:
        load_dotenv(Path(args.env).expanduser().resolve())
        api_key = (
            os.getenv("VISION_API_KEY")
            or os.getenv("API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        base_url = (
            os.getenv("VISION_BASE_URL")
            or os.getenv("BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
        )
        model = (
            args.model
            or os.getenv("VISION_MODEL")
            or os.getenv("MODEL_NAME")
            or os.getenv("OPENAI_MODEL")
        )
        if not api_key or not base_url or not model:
            print("错误: 缺少视觉模型的 API_KEY、BASE_URL 或 MODEL 配置", file=sys.stderr)
            return 1
        client = OpenAI(api_key=api_key, base_url=base_url)
        raw = call_vision_api(
            client,
            model,
            load_text(Path(args.system_prompt).expanduser().resolve()),
            args.prompt,
            image_path,
        )
        if args.raw_out:
            raw_path = Path(args.raw_out).expanduser().resolve()
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(raw, encoding="utf-8")
        items = extract_json_array(raw)

    annotated, drawn = annotate_image(image, items)
    out_image = (
        Path(args.output).expanduser().resolve()
        if args.output
        else image_path.with_name(f"{image_path.stem}_annotated.png")
    )
    out_json = (
        Path(args.json_out).expanduser().resolve()
        if args.json_out
        else image_path.with_name(f"{image_path.stem}_annotations.json")
    )
    out_image.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_image), annotated):
        print(f"错误: 无法写入批注图: {out_image}", file=sys.stderr)
        return 1

    out_json.write_text(
        json.dumps(
            {
                "image": str(image_path),
                "width": int(image.shape[1]),
                "height": int(image.shape[0]),
                "model": model,
                "user_prompt": args.prompt,
                "count": len(drawn),
                "items": drawn,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"检出隐患: {len(drawn)} / 模型返回 {len(items)}")
    print(f"批注图像: {out_image}")
    print(f"标注 JSON: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
