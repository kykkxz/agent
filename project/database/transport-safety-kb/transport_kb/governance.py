from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .models import SourceCandidate


@dataclass(slots=True)
class GovernanceDecision:
    accepted: bool
    notes: list[str]


class SourceGovernance:
    def __init__(self, allowed_domains: list[str], min_text_chars: int = 300) -> None:
        self.allowed_domains = [domain.lower() for domain in allowed_domains]
        self.min_text_chars = min_text_chars

    def evaluate(self, candidate: SourceCandidate, text: str, title: str) -> GovernanceDecision:
        notes: list[str] = []
        host = (urlparse(candidate.source_uri).hostname or "").lower()
        is_configured_local = bool(candidate.extra.get("local_primary_source"))
        if not is_configured_local and not any(
            host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains
        ):
            notes.append(f"来源域名不在白名单: {host or 'missing'}")
        if len(text) < self.min_text_chars:
            notes.append(f"正文不足 {self.min_text_chars} 字符")
        normalized = re.sub(r"\s+", "", f"{title}\n{text}")
        missing = [word for word in candidate.expected_keywords if word not in normalized]
        if missing:
            notes.append(f"缺少预期关键词: {', '.join(missing)}")
        if not candidate.publisher:
            notes.append("发布机构缺失")
        if not candidate.published_at:
            notes.append("发布日期缺失")
        if candidate.license_status not in {"公开发布", "公开许可", "已授权"}:
            notes.append(f"许可状态不可准入: {candidate.license_status}")
        return GovernanceDecision(not notes, notes)


def risk_categories(text: str) -> list[str]:
    mapping = {
        "坍塌": ["坍塌", "基坑", "脚手架"],
        "起重吊装": ["起重", "吊装", "塔吊"],
        "高处作业": ["高处", "坠落"],
        "临时用电与触电": ["触电", "用电"],
        "火灾与动火": ["火灾", "动火"],
        "隧道与地下工程": ["隧道", "地下工程"],
        "道路运营": ["道路", "公路", "运营"],
        "应急管理": ["应急", "救援"],
        "安全生产责任": ["责任", "主要负责人", "生产经营单位"],
        "隐患排查治理": ["隐患", "排查", "治理"],
    }
    found = [category for category, words in mapping.items() if any(word in text for word in words)]
    return found or ["综合安全管理"]
