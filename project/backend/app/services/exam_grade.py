from __future__ import annotations

import json

from app.models.exam import Question


def parse_json(raw: str, default):
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def normalize_answer(value: str) -> str:
    return "".join(str(value or "").split()).upper()


def _resolve(question: Question, user_answer: str) -> str:
    options = parse_json(question.options_json, {})
    raw = str(user_answer or "").strip()
    if raw in options:
        return str(options[raw])
    upper = raw.upper()
    for key, text in options.items():
        if str(key).upper() == upper:
            return str(text)
    return raw


def grade_question(question: Question, user_answer: str) -> tuple[float, bool]:
    if question.type == "essay":
        return 0.0, False
    expected = normalize_answer(question.answer)
    actual = normalize_answer(_resolve(question, user_answer))
    mapping = {
        "TRUE": "正确",
        "FALSE": "错误",
        "对": "正确",
        "错": "错误",
        "1": "正确",
        "0": "错误",
        "A": "正确",
        "B": "错误",
    }
    expected = mapping.get(expected, expected)
    actual = mapping.get(actual, actual)
    if question.type == "multi_choice":
        ok = "".join(sorted(expected)) == "".join(sorted(normalize_answer(user_answer)))
    else:
        ok = expected == actual or expected == normalize_answer(user_answer)
    return (question.score if ok else 0.0, ok)