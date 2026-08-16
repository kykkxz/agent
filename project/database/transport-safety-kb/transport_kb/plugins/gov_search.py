from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import quote

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from ..models import FetchResult, SourceCandidate
from ..transport import CurlTransport
from .base import SourcePlugin


SEARCH_ENDPOINT = (
    "https://sousuoht.www.gov.cn/athena/forward/"
    "2B22E8E39E850E17F95A016A74FCB6B673336FA8B6FEC0E2955907EF9AEE06BE"
)
PUBLIC_KEY_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCSMhMJQ+XLI7oW0k9Bwufur4Ag40tcsrzT7WZf6Ao0"
    "O/hyY1gZtCSYFxkxIZUXjW46j27XSW8IDX1rTJoHaMxHCWsOpTi2W5stybGYZytsY5on8gd8AIaS1d52"
    "h9eaS2TFydtJJtE50xHmT0WmoyoinWCuVCOkdCLhh9b9jSdeSQIDAQAB"
)
FRONTEND_APP_ID = "a46884b2013e4d189f2a8e2d49a23525"


def _frontend_app_key() -> str:
    pem = f"-----BEGIN PUBLIC KEY-----\n{PUBLIC_KEY_B64}\n-----END PUBLIC KEY-----"
    encrypted = PKCS1_v1_5.new(RSA.import_key(pem)).encrypt(FRONTEND_APP_ID.encode("ascii"))
    return quote(base64.b64encode(encrypted).decode("ascii"), safe="")


def _clean_markup(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").replace("<br>", " ").strip()


def _publisher_from_title(title: str, default: str) -> str:
    agencies = (
        "交通运输部办公厅", "交通运输部", "住房和城乡建设部", "住房城乡建设部",
        "应急管理部", "国务院安全生产委员会", "国务院",
    )
    return next((agency for agency in agencies if title.startswith(agency)), default)


class GovSearchPlugin(SourcePlugin):
    """Discover official gov.cn documents through the site's public search frontend API."""

    plugin_name = "official_gov_search_plugin"

    def __init__(self, transport: CurlTransport) -> None:
        self.transport = transport
        self._indexed_by_uri: dict[str, str] = {}

    def discover(self, config: dict[str, Any]) -> list[SourceCandidate]:
        candidates: list[SourceCandidate] = []
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "athenaAppName": quote("国网搜索", safe=""),
            "athenaAppKey": _frontend_app_key(),
        }
        for query in config.get("queries", []):
            payload = {
                "code": "17da70961a7",
                "historySearchWords": [],
                "dataTypeId": 107,
                "orderBy": query.get("order_by", "related"),
                "searchBy": query.get("search_by", "title"),
                "appendixType": "",
                "granularity": "ALL",
                "trackTotalHits": True,
                "beginDateTime": query.get("begin", ""),
                "endDateTime": query.get("end", ""),
                "isSearchForced": 0,
                "filters": [],
                "pageNo": 1,
                "pageSize": min(int(query.get("limit", 5)), 20),
                "customFilter": {"operator": "and", "properties": []},
                "searchWord": query["search_word"],
            }
            result = self.transport.fetch(
                SEARCH_ENDPOINT, method="POST", headers=headers,
                body=json.dumps(payload, ensure_ascii=False),
            )
            if result.status_code != 200:
                raise RuntimeError(
                    f"government search failed for {query['search_word']}: "
                    f"HTTP {result.status_code} {result.error}"
                )
            decoded = json.loads(result.content.decode("utf-8"))
            if decoded.get("resultCode", {}).get("code") != 200:
                raise RuntimeError(f"government search rejected query: {decoded.get('resultCode')}")
            records = decoded["result"]["data"]["middle"]["list"]
            for record in records[: int(query.get("limit", 5))]:
                uri = record.get("url", "")
                title = _clean_markup(record.get("title_no_tag") or record.get("title", ""))
                indexed = _clean_markup(record.get("content") or record.get("summary", ""))
                required_all = query.get("title_required_all", [])
                required_any = query.get("title_required_any", [])
                excluded = query.get("title_exclude", [])
                if required_all and not all(word in title for word in required_all):
                    continue
                if required_any and not any(word in title for word in required_any):
                    continue
                if any(word in title for word in excluded):
                    continue
                if not uri or not title:
                    continue
                metadata = {}
                for rule in query.get("metadata_rules", []):
                    if rule["title_contains"] in title:
                        metadata.update({key: value for key, value in rule.items() if key != "title_contains"})
                self._indexed_by_uri[uri] = indexed
                candidates.append(SourceCandidate(
                    source_id=f"gov-search:{record.get('documentId', uri)}",
                    plugin=self.plugin_name,
                    source_uri=uri,
                    title=title,
                    publisher=metadata.get(
                        "publisher",
                        _publisher_from_title(
                            title, query.get("publisher", record.get("agencies", "中国政府网"))
                        ),
                    ),
                    document_type=query["document_type"],
                    published_at=metadata.get(
                        "published_at", query.get("published_at", (record.get("time") or "")[:10])
                    ),
                    effective_from=metadata.get("effective_from", query.get("effective_from", "")),
                    effective_to=metadata.get("effective_to", query.get("effective_to", "")),
                    version_status=metadata.get(
                        "version_status", query.get("version_status", "待确认")
                    ),
                    jurisdiction=query.get("jurisdiction", "国家"),
                    applicable_role=query.get("applicable_role", []),
                    applicable_activity=query.get("applicable_activity", []),
                    authority_level="A",
                    license_status="公开发布",
                    expected_keywords=query.get("expected_keywords", []),
                    indexed_content=indexed,
                    relation=metadata.get("relation", query.get("relation", "")),
                    extra={
                        "query": query["search_word"],
                        "search_record": record,
                        "source_kind": query["plugin"],
                    },
                ))
        unique: dict[str, SourceCandidate] = {}
        for candidate in candidates:
            unique.setdefault(candidate.source_uri, candidate)
        return list(unique.values())

    def fetch(self, candidate: SourceCandidate) -> FetchResult:
        fetched = self.transport.fetch(candidate.source_uri)
        if fetched.status_code == 200 and len(fetched.content) > 300:
            return fetched
        indexed = candidate.indexed_content or self._indexed_by_uri.get(candidate.source_uri, "")
        if indexed:
            html = f"<html><head><title>{candidate.title}</title></head><body><article>{indexed}</article></body></html>"
            return FetchResult(
                candidate.source_uri,
                candidate.source_uri,
                200,
                "text/html",
                html.encode("utf-8"),
                "gov-search-index-fallback",
                fetched.error or f"origin returned HTTP {fetched.status_code}",
            )
        return fetched
