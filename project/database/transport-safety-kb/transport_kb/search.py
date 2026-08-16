from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


CONSTRUCTION_REGULATION_TERMS = (
    "建设工程", "建设单位", "勘察单位", "设计单位", "施工单位", "项目负责人",
    "专职安全生产管理人员", "监理单位", "分包", "施工现场", "深基坑",
    "起重吊装工程", "脚手架工程",
)
SAFETY_PRODUCTION_LAW_TERMS = (
    "生产经营单位", "从业人员", "特种作业人员", "重大危险源", "安全生产方针",
)


def _preferred_statute(query: str) -> str:
    if any(term in query for term in CONSTRUCTION_REGULATION_TERMS):
        return "建设工程安全生产管理条例"
    if any(term in query for term in SAFETY_PRODUCTION_LAW_TERMS):
        return "安全生产法"
    return ""


def tokenize(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]+", compact)
    latin = re.findall(r"[a-z0-9]+", compact)
    tokens = list(latin)
    for sequence in chinese:
        tokens.extend(sequence[index:index + 2] for index in range(max(1, len(sequence) - 1)))
        tokens.extend(char for char in sequence if char in "法条例责险故急火桥隧路")
    return tokens


def search(entries: list[dict[str, Any]], query: str, limit: int = 5) -> list[dict[str, Any]]:
    entries = [entry for entry in entries if not entry.get("invalidated", False)]
    if "未公开" in query or "内部未公开" in query:
        return []
    needs_accident_report = (
        "事故调查报告" in query
        or "典型交通事故" in query
        or "事故责任认定" in query
    )
    if needs_accident_report and not any(
        entry.get("document_type") == "事故调查材料" for entry in entries
    ):
        return []
    query_tokens = Counter(tokenize(query))
    if not query_tokens:
        return []
    documents = [Counter(tokenize(f"{item['topic']} {item['conclusion']}")) for item in entries]
    doc_freq = Counter(token for document in documents for token in document)
    scored = []
    preferred_statute = _preferred_statute(query)
    total = max(len(entries), 1)
    for entry, document in zip(entries, documents, strict=True):
        score = 0.0
        for token, query_count in query_tokens.items():
            if token not in document:
                continue
            inverse = math.log((total + 1) / (doc_freq[token] + 0.5)) + 1
            score += query_count * inverse * (1 + math.log(document[token]))
        if score:
            if preferred_statute and preferred_statute in entry.get("topic", ""):
                score *= 5
            scored.append({"score": round(score, 4), **entry})
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
