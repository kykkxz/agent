from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from transport_kb.storage import write_json  # noqa: E402
from transport_kb.transport import CurlTransport  # noqa: E402


ACCIDENT_RELEVANCE = (
    "高速", "公路", "道路", "交通", "隧道", "桥", "铁路", "轨道", "港", "船",
    "运输", "车辆", "叉车", "汽车", "项目", "工地", "建设", "工程", "高处坠落",
    "高坠", "物体打击", "坍塌", "触电", "机械伤害", "窒息", "有限空间", "塔吊",
    "起重", "施工", "管网", "清淤", "泵站",
)
ACCIDENT_EXCLUDE = ("煤矿", "酒店", "医院", "养老", "居民自建房", "住宅")
DATE_PATTERNS = (
    re.compile(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})"),
    re.compile(r"(20\d{2})(\d{2})(\d{2})"),
)
SOURCE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "mem": {
        "name": "应急管理部调查报告",
        "index_urls": ["https://www.mem.gov.cn/gk/sgcc/tbzdsgdcbg/"]
        + [f"https://www.mem.gov.cn/gk/sgcc/tbzdsgdcbg/index_{index}.shtml" for index in range(1, 7)],
    },
    "hcq": {
        "name": "惠城区生产安全事故调查报告",
        "index_urls": ["https://www.hcq.gov.cn/hcqzdlyxxgk/aqscxxgk/scaqsgdcbg/"]
        + [
            f"https://www.hcq.gov.cn/hcqzdlyxxgk/aqscxxgk/scaqsgdcbg/index_{index}.html"
            for index in range(2, 6)
        ],
    },
    "huli": {
        "name": "厦门市湖里区事故调查督办",
        "index_urls": ["https://www.huli.gov.cn/zwgk/xzdgk/42565/4407/"],
    },
}
SOURCE_URI_OVERRIDES = {
    "https://www.mem.gov.cn/gk/sgcc/tbzdsgdcbg/2020/202009/t20200911_365513.shtml":
        "https://www.mem.gov.cn/gk/sgcc/tbzdsgdcbg/2020/202009/W020240229368623786873.pdf",
}


def _clean(value: str) -> str:
    return " ".join(value.replace("\u3000", " ").split())


def _stable_source_id(uri: str) -> str:
    return f"official-accident-{hashlib.sha256(uri.encode('utf-8')).hexdigest()[:20]}"


def _extract_date(*values: str) -> str:
    for value in values:
        for pattern in DATE_PATTERNS:
            match = pattern.search(value)
            if match:
                year, month, day = (int(part) for part in match.groups())
                if 2000 <= year <= datetime.now().year and 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def _publisher(host: str) -> tuple[str, str]:
    if host.endswith("mem.gov.cn"):
        return "中华人民共和国应急管理部", "国家"
    if host.endswith("hcq.gov.cn"):
        return "惠州市惠城区人民政府", "广东省惠州市惠城区"
    if host.endswith("huli.gov.cn"):
        return "厦门市湖里区人民政府", "福建省厦门市湖里区"
    return host, "地方"


def _candidate_record(
    page_uri: str, indexed_title: str, context: str, index_url: str, index_name: str
) -> dict[str, Any]:
    title = re.sub(r"\s+20\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2}日?$", "", indexed_title).strip()
    published_at = _extract_date(indexed_title, context, page_uri)
    host = (urlparse(page_uri).hostname or "").lower()
    publisher, jurisdiction = _publisher(host)
    return {
        "source_id": _stable_source_id(page_uri),
        "source_uri": page_uri,
        "title": title,
        "publisher": publisher,
        "document_type": "事故调查材料",
        "published_at": published_at,
        "version_status": "不适用",
        "jurisdiction": jurisdiction,
        "applicable_role": ["交通建设单位", "交通运输企业", "施工单位"],
        "applicable_activity": ["事故复盘", "整改治理", "安全培训"],
        "authority_level": "A",
        "license_status": "公开发布",
        "expected_keywords": ["事故"],
        "relation": "",
        "extra": {
            "discovery_method": "official_index_crawler",
            "discovered_from": index_url,
            "index_name": index_name,
            "source_page": page_uri,
            "browser_index_verified": True,
            "detail_probe_deferred": True,
        },
    }


def _anchor_context(anchor: Any) -> str:
    container = anchor.find_parent(["li", "tr", "article"])
    if container is None:
        container = anchor.parent or anchor
    return _clean(container.get_text(" ", strip=True))


def _read_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()


def collect_source(
    source_key: str,
    *,
    transport: CurlTransport,
    checkpoint_path: Path,
    limit: int = 0,
    failure_path: Path | None = None,
) -> dict[str, int]:
    definition = SOURCE_DEFINITIONS[source_key]
    existing = {record["source_uri"]: record for record in _read_jsonl([checkpoint_path])}
    discovered: dict[str, dict[str, Any]] = {}
    failed_indexes = 0
    urls = definition["index_urls"]
    for position, index_url in enumerate(urls, 1):
        started = time.monotonic()
        print(f"[{source_key}] index {position}/{len(urls)} {index_url}", flush=True)
        fetched = transport.fetch(index_url)
        elapsed = time.monotonic() - started
        print(f"[{source_key}] HTTP {fetched.status_code} in {elapsed:.1f}s", flush=True)
        if fetched.status_code != 200 or not fetched.content:
            failed_indexes += 1
            if failure_path is not None:
                _append_jsonl(failure_path, {
                    "source": source_key,
                    "index_url": index_url,
                    "status_code": fetched.status_code,
                    "error": fetched.error,
                    "failed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                })
            continue
        soup = BeautifulSoup(fetched.content, "html.parser")
        for anchor in soup.select("a[href]"):
            indexed_title = _clean(anchor.get_text(" ", strip=True))
            if not ("调查报告" in indexed_title or "调查评估报告" in indexed_title):
                continue
            if not any(keyword in indexed_title for keyword in ACCIDENT_RELEVANCE):
                continue
            if any(keyword in indexed_title for keyword in ACCIDENT_EXCLUDE):
                continue
            page_uri = urljoin(fetched.final_uri, anchor.get("href", ""))
            if page_uri.rstrip("/") == fetched.final_uri.rstrip("/"):
                continue
            context = _anchor_context(anchor)
            discovered.setdefault(
                page_uri,
                _candidate_record(
                    page_uri, indexed_title, context, index_url, str(definition["name"])
                ),
            )

    selected = list(discovered.values())[:limit or None]
    written = 0
    updated = 0
    for record in selected:
        previous = existing.get(record["source_uri"])
        if previous == record:
            continue
        _append_jsonl(checkpoint_path, record)
        existing[record["source_uri"]] = record
        written += 1
        updated += int(previous is not None)
        print(f"[{source_key}] checkpoint {record['title']}", flush=True)
    return {
        "discovered": len(discovered),
        "selected": len(selected),
        "written": written,
        "updated": updated,
        "failed_indexes": failed_indexes,
    }


def finalize_catalog(checkpoint_paths: Iterable[Path], output: Path) -> dict[str, Any]:
    unique: dict[str, dict[str, Any]] = {}
    for original in _read_jsonl(checkpoint_paths):
        record = dict(original)
        source_page = record["source_uri"]
        attachment = SOURCE_URI_OVERRIDES.get(source_page)
        if attachment:
            record["source_uri"] = attachment
            record["source_id"] = _stable_source_id(attachment)
            record["relation"] = f"原发布页面：{source_page}"
            record["extra"] = {**record.get("extra", {}), "source_page": source_page,
                               "attachment_verified": True}
        unique[record["source_uri"]] = record
    sources = sorted(
        unique.values(),
        key=lambda item: item["source_uri"],
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_count": len(sources),
        "sources": sources,
    }
    write_json(output, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="从已核验官方栏目生成可恢复的采集目录")
    parser.add_argument("--source", choices=["all", *SOURCE_DEFINITIONS], default="all")
    parser.add_argument("--limit", type=int, default=0, help="每个来源最多选择的候选数；0 表示不限")
    parser.add_argument("--checkpoint-dir", type=Path, default=PROJECT_ROOT / "data" / "discovery_checkpoints")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "config" / "generated_sources.json")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error("--limit must be zero or greater")

    keys = list(SOURCE_DEFINITIONS) if args.source == "all" else [args.source]
    checkpoint_paths = [args.checkpoint_dir / f"{key}.jsonl" for key in SOURCE_DEFINITIONS]
    if not args.finalize_only:
        transport = CurlTransport(args.timeout)
        for key in keys:
            result = collect_source(
                key,
                transport=transport,
                checkpoint_path=args.checkpoint_dir / f"{key}.jsonl",
                limit=args.limit,
                failure_path=args.checkpoint_dir / f"{key}.failures.jsonl",
            )
            print(json.dumps({"source": key, **result}, ensure_ascii=False), flush=True)
    catalog = finalize_catalog(checkpoint_paths, args.output)
    print(json.dumps({"output": str(args.output), "sources": catalog["source_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
