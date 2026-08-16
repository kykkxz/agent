from __future__ import annotations

from app.services.hazard_annotation import extract_json_array, to_pixel_bbox


def test_extract_json_array_from_wrapped_response() -> None:
    payload = '```json\n{"items": [{"id": 1, "label": "临边防护缺失"}]}\n```'

    assert extract_json_array(payload) == [{"id": 1, "label": "临边防护缺失"}]


def test_to_pixel_bbox_converts_and_normalizes_coordinates() -> None:
    item = {"bbox_norm": [0.8, 0.75, 0.2, 0.25]}

    assert to_pixel_bbox(item, width=1000, height=600) == (200, 150, 800, 450)
