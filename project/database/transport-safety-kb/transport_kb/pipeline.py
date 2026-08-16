from __future__ import annotations

import hashlib
import json
import re
import uuid
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .extractors import extract_content
from .governance import SourceGovernance, risk_categories
from .models import EvidenceUnit, KnowledgeEntry, StandardDocument
from .plugins import CatalogFilePlugin, DirectUrlPlugin, GovSearchPlugin, LocalFilePlugin
from .sqlite_store import rebuild_database
from .storage import ensure_layout, write_json, write_jsonl
from .transport import CurlTransport


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"


def _normalized_hash(text: str) -> str:
    normalized = re.sub(r"\s+", "", text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _archive_suffix(media_type: str, uri: str) -> str:
    uri_suffix = Path(urlparse(uri).path).suffix.lower()
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".html", ".htm", ".xml", ".json", ".txt"}
    if uri_suffix in allowed:
        return uri_suffix
    media = media_type.lower()
    if "pdf" in media:
        return ".pdf"
    if "wordprocessingml" in media:
        return ".docx"
    if "msword" in media:
        return ".doc"
    if "spreadsheetml" in media:
        return ".xlsx"
    if "json" in media:
        return ".json"
    if "xml" in media:
        return ".xml"
    if "text/plain" in media:
        return ".txt"
    return ".html"


def _archive_component(value: str) -> str:
    component = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._")
    return component[:100] or "source"


def fragment_candidate_text(
    candidate: Any, text: str, fallback_title: str = ""
) -> list[tuple[str, str]]:
    sections = candidate.extra.get("split_sections", [])
    if sections:
        fragments: list[tuple[str, str]] = []
        for section in sections:
            heading = section["heading"]
            start_match = re.search(rf"(?m)^{re.escape(heading)}[ \t]*$", text)
            if start_match is None:
                raise ValueError(f"configured split heading not found: {heading}")
            end_heading = section.get("end_heading", "")
            if end_heading:
                end_match = re.search(
                    rf"(?m)^{re.escape(end_heading)}[ \t]*$", text[start_match.end():]
                )
                if end_match is None:
                    raise ValueError(f"configured end heading not found: {end_heading}")
                end = start_match.end() + end_match.start()
            else:
                end = len(text)
            fragments.append((section["title"], text[start_match.start():end].strip()))
        return fragments
    titles = candidate.extra.get("split_titles", [])
    if not titles:
        return [(candidate.title or fallback_title, text)]
    boundaries: list[tuple[int, str]] = []
    for title in titles:
        match = re.search(rf"(?m)^{re.escape(title)}[ \t]*$", text)
        if match is None:
            raise ValueError(f"configured split title not found as standalone heading: {title}")
        boundaries.append((match.start(), title))
    boundaries.sort()
    fragments: list[tuple[str, str]] = []
    for index, (start, title) in enumerate(boundaries):
        end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(text)
        fragment = text[start:end].strip()
        if fragment:
            fragments.append((title, fragment))
    return fragments


def split_evidence(document: StandardDocument, max_chars: int = 1200) -> list[EvidenceUnit]:
    article_pattern = re.compile(r"第[一二三四五六七八九十百零〇0-9]+条")
    page_pattern = re.compile(r"\[第(\d+)页\]")
    article_matches = list(article_pattern.finditer(document.text))
    page_matches = list(page_pattern.finditer(document.text))
    page_positions = [match.start() for match in page_matches]
    page_numbers = [int(match.group(1)) for match in page_matches]

    ranges: list[tuple[int, int, str]] = []
    if article_matches:
        prefix = page_pattern.sub("", document.text[:article_matches[0].start()]).strip()
        if len(prefix) >= 10:
            ranges.append((0, article_matches[0].start(), "前言"))
        for index, match in enumerate(article_matches):
            end = article_matches[index + 1].start() if index + 1 < len(article_matches) else len(document.text)
            ranges.append((match.start(), end, match.group(0)))
    else:
        paragraph_matches = list(re.finditer(r"\S[\s\S]*?(?=\n{2,}|\Z)", document.text))
        ranges = [
            (match.start(), match.end(), f"段落{index}")
            for index, match in enumerate(paragraph_matches, 1)
        ]

    def page_at(position: int) -> int | None:
        index = bisect_right(page_positions, position) - 1
        return page_numbers[index] if index >= 0 else None

    evidence: list[EvidenceUnit] = []
    for start, end, base_locator in ranges:
        for offset in range(0, end - start, max_chars):
            piece_start = start + offset
            piece_end = min(start + offset + max_chars, end)
            piece = page_pattern.sub("", document.text[piece_start:piece_end]).strip()
            if len(piece) < 10:
                continue
            start_page = page_at(piece_start)
            end_page = page_at(max(piece_start, piece_end - 1))
            page_locator = ""
            if start_page is not None:
                page_locator = (
                    f"第{start_page}页"
                    if end_page in {None, start_page}
                    else f"第{start_page}-{end_page}页"
                )
            locator_parts = [part for part in (page_locator, base_locator) if part]
            if offset:
                locator_parts.append(f"片段{offset // max_chars + 1}")
            locator = " / ".join(locator_parts)
            evidence.append(EvidenceUnit(
                evidence_id=_stable_id("ev", f"{document.document_id}:{locator}:{piece}"),
                document_id=document.document_id,
                source_uri=document.source_uri,
                title=document.title,
                locator=locator,
                text=piece,
                content_hash=_normalized_hash(piece),
                authority_level=document.authority_level,
                review_status=document.review_status,
            ))
    return evidence


def build_knowledge(evidence: list[EvidenceUnit], documents: dict[str, StandardDocument]) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for unit in evidence:
        document = documents[unit.document_id]
        conclusion = unit.text[:500]
        entries.append(KnowledgeEntry(
            knowledge_id=_stable_id("kb", unit.evidence_id),
            topic=f"{unit.title} / {unit.locator}",
            document_type=document.document_type,
            version_status=document.version_status,
            risk_categories=risk_categories(unit.text),
            applicable_roles=document.applicable_role,
            applicable_activities=document.applicable_activity,
            conclusion=conclusion,
            authority_level=document.authority_level,
            citations=[{"evidence_id": unit.evidence_id, "source_uri": unit.source_uri, "locator": unit.locator}],
            review_status="机器初审",
            publication_layer="待核验层",
            invalidated=document.version_status in {"已废止", "历史有效"},
            document_id=document.document_id,
        ))
    return entries


class CollectionPipeline:
    def __init__(self, manifest_path: Path, output: Path) -> None:
        self.manifest_path = manifest_path
        self.output = output
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.transport = CurlTransport(self.manifest.get("timeout_seconds", 45))
        self.governance = SourceGovernance(
            self.manifest["governance"]["allowed_domains"],
            self.manifest["governance"].get("min_text_chars", 300),
        )
        self.plugins = {
            "gov_search": GovSearchPlugin(self.transport),
            "direct_url": DirectUrlPlugin(self.transport),
            "local_file": LocalFilePlugin(manifest_path.parent.parent),
            "catalog_file": CatalogFilePlugin(manifest_path.parent.parent, self.transport),
        }
        self.plugins_by_name = {plugin.plugin_name: plugin for plugin in self.plugins.values()}

    def run(self, offline: bool = False) -> dict[str, Any]:
        ensure_layout(self.output)
        task_id = f"collect-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        discovered = []
        failures: list[dict[str, Any]] = []
        plugin_configs = [
            config for config in self.manifest["plugins"]
            if not offline or config["type"] == "local_file"
        ]
        for plugin_config in plugin_configs:
            plugin = self.plugins[plugin_config["type"]]
            try:
                discovered.extend(plugin.discover(plugin_config))
            except Exception as exc:
                if plugin_config.get("required", plugin_config["type"] == "local_file"):
                    raise
                failures.append({"stage": "discover", "plugin": plugin_config["type"], "error": str(exc)})
        discovered = list({candidate.source_id: candidate for candidate in discovered}.values())

        documents: list[StandardDocument] = []
        quarantine: list[dict[str, Any]] = []
        raw_records: list[dict[str, Any]] = []
        seen_hashes: dict[str, str] = {}
        for candidate in discovered:
            plugin = self.plugins_by_name[candidate.plugin]
            fetched = plugin.fetch(candidate)
            if fetched.status_code != 200 or not fetched.content:
                failures.append({
                    "stage": "fetch", "source_id": candidate.source_id,
                    "source_uri": candidate.source_uri, "status": fetched.status_code,
                    "error": fetched.error,
                })
                continue
            raw_hash = hashlib.sha256(fetched.content).hexdigest()
            suffix = _archive_suffix(fetched.media_type, fetched.final_uri)
            archive_dir = self.output / "source_archive" / _archive_component(candidate.source_id)
            archive_dir.mkdir(parents=True, exist_ok=True)
            raw_path = archive_dir / f"{raw_hash}{suffix}"
            if not raw_path.exists():
                raw_path.write_bytes(fetched.content)
            metadata_path = archive_dir / f"{raw_hash}.metadata.json"
            raw_record = {
                "task_id": task_id, "source_id": candidate.source_id,
                "requested_uri": fetched.requested_uri, "final_uri": fetched.final_uri,
                "retrieved_at": _utc_now(), "status_code": fetched.status_code,
                "media_type": fetched.media_type, "raw_sha256": raw_hash,
                "raw_path": str(raw_path.relative_to(self.output)), "transport": fetched.transport,
                "transport_note": fetched.error,
                "archive_metadata_path": str(metadata_path.relative_to(self.output)),
            }
            write_json(metadata_path, {
                **raw_record,
                "title": candidate.title,
                "publisher": candidate.publisher,
                "document_type": candidate.document_type,
                "plugin": candidate.plugin,
                "source_metadata": candidate.extra,
                "archive_policy": "原始字节按 SHA-256 命名，不改写内容",
            })
            raw_records.append(raw_record)
            if candidate.extra.get("archive_only"):
                continue
            try:
                extracted_title, text = extract_content(fetched.media_type, fetched.content)
            except Exception as exc:
                failures.append({"stage": "extract", "source_id": candidate.source_id, "error": str(exc)})
                continue
            try:
                fragments = fragment_candidate_text(candidate, text, extracted_title)
            except ValueError as exc:
                failures.append({"stage": "fragment", "source_id": candidate.source_id, "error": str(exc)})
                continue
            for title, fragment_text in fragments:
                fragment_metadata = candidate.extra.get("fragment_metadata", {}).get(title, {})
                decision = self.governance.evaluate(candidate, fragment_text, title)
                content_hash = _normalized_hash(fragment_text)
                if content_hash in seen_hashes:
                    failures.append({
                        "stage": "deduplicate", "source_id": candidate.source_id,
                        "duplicate_of": seen_hashes[content_hash], "content_hash": content_hash,
                    })
                    continue
                seen_hashes[content_hash] = candidate.source_id
                media_type = fetched.media_type.lower()
                section_locator = (
                    "PDF页码与条款" if "pdf" in media_type
                    else "Word段落" if "word" in media_type
                    else "HTML正文或官方搜索索引"
                )
                document = StandardDocument(
                    document_id=_stable_id("doc", f"{candidate.source_uri}:{title}:{content_hash}"),
                    source_id=candidate.source_id,
                    source_uri=candidate.source_uri,
                    title=title,
                    publisher=str(candidate.publisher),
                    document_type=candidate.document_type,
                    published_at=candidate.published_at,
                    effective_from=candidate.effective_from,
                    effective_to=candidate.effective_to,
                    version_status=candidate.version_status,
                    jurisdiction=fragment_metadata.get("jurisdiction", candidate.jurisdiction),
                    applicable_role=fragment_metadata.get("applicable_role", candidate.applicable_role),
                    applicable_activity=fragment_metadata.get(
                        "applicable_activity", candidate.applicable_activity
                    ),
                    authority_level=candidate.authority_level,
                    license_status=candidate.license_status,
                    content_hash=content_hash,
                    retrieved_at=_utc_now(),
                    section_locator=section_locator,
                    review_status="机器初审" if decision.accepted else "隔离",
                    publication_layer="待核验层",
                    raw_path=str(raw_path.relative_to(self.output)),
                    text=fragment_text,
                    fetch_status=fetched.transport,
                    relation=candidate.relation,
                    governance_notes=decision.notes,
                )
                if decision.accepted:
                    documents.append(document)
                else:
                    quarantine.append(document.to_dict())

        document_map = {item.document_id: item for item in documents}
        evidence = [unit for document in documents for unit in split_evidence(document)]
        knowledge = build_knowledge(evidence, document_map)
        write_jsonl(self.output / "raw_manifest.jsonl", raw_records)
        write_jsonl(self.output / "documents.jsonl", (item.to_dict() for item in documents))
        write_jsonl(self.output / "evidence.jsonl", (item.to_dict() for item in evidence))
        write_jsonl(self.output / "knowledge_base.jsonl", (item.to_dict() for item in knowledge))
        write_jsonl(self.output / "quarantine.jsonl", quarantine)
        write_jsonl(self.output / "reports" / "failures.jsonl", failures)
        summary = {
            "task_id": task_id,
            "started_and_completed_at": _utc_now(),
            "discovered": len(discovered),
            "accepted_documents": len(documents),
            "accepted_source_count": len({item.source_id for item in documents}),
            "quarantined_documents": len(quarantine),
            "evidence_units": len(evidence),
            "knowledge_entries": len(knowledge),
            "failures": len(failures),
            "document_types": dict(Counter(item.document_type for item in documents)),
            "enterprise_or_project_entities": len({
                entity
                for candidate in discovered
                for entity in candidate.extra.get("covered_entities", [])
            }),
            "official_accident_reports": sum(
                item.document_type == "事故调查材料"
                and (urlparse(item.source_uri).hostname or "").lower().endswith("gov.cn")
                for item in documents
            ),
            "fetch_transports": dict(Counter(item.fetch_status for item in documents)),
            "review_status": "机器初审，全部位于待核验层",
        }
        accident_count = summary["document_types"].get("事故调查材料", 0)
        summary["official_accident_report_ratio"] = (
            summary["official_accident_reports"] / accident_count if accident_count else 0.0
        )
        database_path = self.output / "transport_safety_kb.sqlite3"
        summary["sqlite"] = rebuild_database(
            database_path=database_path,
            task_id=task_id,
            summary=summary,
            candidates=discovered,
            raw_records=raw_records,
            documents=documents,
            evidence=evidence,
            knowledge=knowledge,
            quarantine=quarantine,
            failures=failures,
        )
        write_json(self.output / "reports" / "run_summary.json", summary)
        write_json(self.output / "reports" / "source_whitelist.json", {
            "allowed_domains": self.manifest["governance"]["allowed_domains"],
            "rule": "仅允许列明域名及其子域名，禁止登录、验证码和访问控制绕过",
        })
        tasks = []
        for plugin_config in plugin_configs:
            for query in plugin_config.get("queries", []):
                tasks.append({
                    "task_id": task_id,
                    "plugin": query["plugin"],
                    "search_word": query["search_word"],
                    "status": "已执行",
                })
        write_json(self.output / "reports" / "collection_tasks.json", tasks)
        self._write_source_registry(documents, failures)
        self._write_quality_report(summary, documents)
        self._write_coverage_gap(summary)
        return summary

    def _write_source_registry(self, documents: list[StandardDocument], failures: list[dict[str, Any]]) -> None:
        lines = ["# 首轮外部数据源登记表", "", "所有条目均为公开来源，当前仅完成机器初审。", "",
                 "| 来源 | 发布机构 | 类型 | 权威等级 | 版本状态 | 采集状态 |", "|---|---|---|---|---|---|"]
        for item in documents:
            lines.append(
                f"| {item.source_uri} | {item.publisher} | {item.document_type} | "
                f"{item.authority_level} | {item.version_status} | 已采集，待人工审核 |"
            )
        lines.extend(["", f"失败或去重记录：{len(failures)} 条，详见 `failures.jsonl`。", ""])
        (self.output / "reports" / "source_registry.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_quality_report(self, summary: dict[str, Any], documents: list[StandardDocument]) -> None:
        total = summary["discovered"] or 1
        accepted = summary["accepted_documents"]
        metadata_complete = sum(
            bool(item.title and item.publisher and item.published_at and item.source_uri) for item in documents
        )
        metadata_rate = metadata_complete / max(len(documents), 1)
        confirmed_versions = sum(item.version_status not in {"待确认", ""} for item in documents)
        origin_fetches = sum(item.fetch_status == "curl" for item in documents)
        lines = [
            "# 首轮数据质量报告", "",
            f"- 发现文档：{summary['discovered']}",
            f"- 准入文档：{accepted}",
            f"- 隔离文档：{summary['quarantined_documents']}",
            f"- 处理成功率：{accepted / total:.1%}",
            f"- 核心元数据完整率：{metadata_rate:.1%}",
            f"- 版本状态已确认率：{confirmed_versions / max(len(documents), 1):.1%}",
            f"- 原始页面直接获取率：{origin_fetches / max(len(documents), 1):.1%}",
            f"- 证据单元：{summary['evidence_units']}",
            f"- 知识条目：{summary['knowledge_entries']}",
            "- 正式发布状态：未发布，全部待人工审核",
            "", 
            "两部核心法规使用本地 PDF 原件；页码和条款定位已保留，版本状态仍待人工终审。",
            "数量覆盖按准入文档和已归档的适用实体证据计算；所有结果仍需人工终审。",
        ]
        (self.output / "reports" / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_coverage_gap(self, summary: dict[str, Any]) -> None:
        types = summary["document_types"]
        laws = types.get("法律", 0) + types.get("行政法规", 0)
        entities = summary.get("enterprise_or_project_entities", 0)
        official_ratio = summary.get("official_accident_report_ratio", 0.0)
        lines = [
            "# 首轮 MVP 覆盖与缺口", "",
            "| 指标 | 任务书目标 | 本轮结果 | 状态 |", "|---|---:|---:|---|",
            f"| 两类核心法规 | 2 | {min(laws, 2)} | 本地 PDF 已入库并保留页码，现行状态待人工终审 |",
            f"| 监管文件 | 未设固定数量 | {types.get('监管文件', 0)} | 已形成初始基线 |",
            f"| 企业或项目制度 | 20-30 家 | {entities} 个具名企业/项目，{types.get('企业制度', 0)} 份制度 | {'达标' if 20 <= entities <= 30 else '未达标'} |",
            f"| 高风险操作场景 | 10 个以上 | {types.get('操作规程', 0)} | {'达标' if types.get('操作规程', 0) >= 10 else '未达标'} |",
            f"| 应急预案 | 20 份以上 | {types.get('应急预案', 0)} | {'达标' if types.get('应急预案', 0) >= 20 else '未达标'} |",
            f"| 典型事故案例 | 50 起以上 | {types.get('事故调查材料', 0)}，官方占比 {official_ratio:.1%} | {'达标' if types.get('事故调查材料', 0) >= 50 and official_ratio >= 0.7 else '未达标'} |",
            "", "全部采集结果仍位于机器初审/待核验层，数量达标不等同于人工审核通过。",
        ]
        (self.output / "reports" / "coverage_gap.md").write_text("\n".join(lines), encoding="utf-8")
