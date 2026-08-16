from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceCandidate:
    source_id: str
    plugin: str
    source_uri: str
    title: str
    publisher: str
    document_type: str
    published_at: str = ""
    effective_from: str = ""
    effective_to: str = ""
    version_status: str = "待确认"
    jurisdiction: str = "国家"
    applicable_role: list[str] = field(default_factory=list)
    applicable_activity: list[str] = field(default_factory=list)
    authority_level: str = "A"
    license_status: str = "公开发布"
    expected_keywords: list[str] = field(default_factory=list)
    indexed_content: str = ""
    relation: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchResult:
    requested_uri: str
    final_uri: str
    status_code: int
    media_type: str
    content: bytes
    transport: str
    error: str = ""


@dataclass(slots=True)
class StandardDocument:
    document_id: str
    source_id: str
    source_uri: str
    title: str
    publisher: str
    document_type: str
    published_at: str
    effective_from: str
    effective_to: str
    version_status: str
    jurisdiction: str
    applicable_role: list[str]
    applicable_activity: list[str]
    authority_level: str
    license_status: str
    content_hash: str
    retrieved_at: str
    section_locator: str
    review_status: str
    publication_layer: str
    raw_path: str
    text: str
    fetch_status: str
    relation: str = ""
    governance_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceUnit:
    evidence_id: str
    document_id: str
    source_uri: str
    title: str
    locator: str
    text: str
    content_hash: str
    authority_level: str
    review_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KnowledgeEntry:
    knowledge_id: str
    topic: str
    document_type: str
    version_status: str
    risk_categories: list[str]
    applicable_roles: list[str]
    applicable_activities: list[str]
    conclusion: str
    authority_level: str
    citations: list[dict[str, str]]
    review_status: str
    publication_layer: str
    invalidated: bool
    document_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
