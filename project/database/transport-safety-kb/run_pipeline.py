from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transport_kb.cli import evaluate
from transport_kb.pipeline import CollectionPipeline
from transport_kb.sqlite_store import verify_database
from transport_kb.storage import write_json


PROJECT_ROOT = Path(__file__).resolve().parent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="交通建设与运营安全知识库闭环采集")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "config" / "sources.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument(
        "--questions",
        type=Path,
        default=PROJECT_ROOT / "config" / "acceptance_questions.json",
    )
    parser.add_argument("--offline", action="store_true", help="仅处理本地原件，不访问网络")
    return parser


def _validate(manifest_path: Path, questions_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"采集配置不存在: {manifest_path}")
    if not questions_path.is_file():
        raise FileNotFoundError(f"验收问题不存在: {questions_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    known_plugins = {"local_file", "direct_url", "gov_search", "catalog_file"}
    for config in manifest.get("plugins", []):
        if config.get("type") not in known_plugins:
            raise ValueError(f"未知插件类型: {config.get('type')}")
    local_configs = [item for item in manifest.get("plugins", []) if item.get("type") == "local_file"]
    if not local_configs:
        raise ValueError("配置必须包含 local_file 插件")
    project_root = manifest_path.parent.parent
    for config in local_configs:
        for source in config.get("sources", []):
            path = Path(source["path"])
            resolved = path if path.is_absolute() else project_root / path
            if not resolved.is_file():
                raise FileNotFoundError(f"本地原件不存在: {resolved.resolve()}")
    return manifest


def _write_final_report(
    output: Path,
    offline: bool,
    summary: dict[str, Any],
    acceptance: dict[str, Any],
    sqlite_check: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    report = {
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "offline" if offline else "online",
        "status": "通过" if not errors else "失败",
        "errors": errors,
        "collection": summary,
        "acceptance": {
            "questions": acceptance["questions"],
            "top5_hits": acceptance["top5_hits"],
            "top5_hit_rate": acceptance["top5_hit_rate"],
            "citation_complete_rate": acceptance["citation_complete_rate"],
        },
        "sqlite": sqlite_check,
        "archive_directory": str(output / "source_archive"),
    }
    write_json(output / "reports" / "final_run_report.json", report)
    lines = [
        "# 知识库闭环运行报告",
        "",
        f"- 状态：{report['status']}",
        f"- 模式：{report['mode']}",
        f"- 准入文档：{summary['accepted_documents']}",
        f"- 证据单元：{summary['evidence_units']}",
        f"- 知识条目：{summary['knowledge_entries']}",
        f"- 固定问题命中率：{acceptance['top5_hit_rate']:.1%}",
        f"- SQLite 完整性：{', '.join(sqlite_check['integrity_check'])}",
        f"- SQLite 外键违规：{len(sqlite_check['foreign_key_violations'])}",
        f"- 原档目录：{output / 'source_archive'}",
        "",
    ]
    if errors:
        lines.extend(["## 失败原因", "", *[f"- {error}" for error in errors], ""])
    else:
        lines.append("本轮采集、原档归档、结构化入库、检索验收和数据库自检已闭环。")
    (output / "reports" / "final_run_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    try:
        _validate(args.manifest, args.questions)
        summary = CollectionPipeline(args.manifest, args.output).run(offline=args.offline)
        acceptance = evaluate(args.output, args.questions)
        sqlite_check = verify_database(args.output / "transport_safety_kb.sqlite3")
        errors: list[str] = []
        if summary["accepted_documents"] < 2:
            errors.append("两部本地核心法规未全部准入")
        if sqlite_check["integrity_check"] != ["ok"]:
            errors.append("SQLite 完整性检查未通过")
        if sqlite_check["foreign_key_violations"]:
            errors.append("SQLite 存在外键违规")
        if sqlite_check["counts"]["raw_assets"] < summary["accepted_source_count"]:
            errors.append("原档数量少于准入来源数量")
        if not args.offline and summary["document_types"].get("监管文件", 0) < 1:
            errors.append("在线采集未形成监管文件基线")
        if not args.offline and summary["document_types"].get("事故调查材料", 0) < 50:
            errors.append("典型事故案例少于 50 起")
        if not args.offline and summary.get("official_accident_report_ratio", 0.0) < 0.7:
            errors.append("官方事故调查报告占比低于 70%")
        if not args.offline and summary["document_types"].get("应急预案", 0) < 20:
            errors.append("应急预案少于 20 份")
        if not args.offline and summary["document_types"].get("操作规程", 0) < 10:
            errors.append("高风险操作场景少于 10 个")
        if not args.offline and summary.get("enterprise_or_project_entities", 0) < 20:
            errors.append("公开企业或项目制度覆盖实体少于 20 个")
        if not args.offline and acceptance["top5_hit_rate"] < 0.85:
            errors.append("固定问题 Top 5 命中率低于 85%")
        if not args.offline and acceptance["citation_complete_rate"] < 0.95:
            errors.append("知识条目引用完整率低于 95%")
        report = _write_final_report(
            args.output, args.offline, summary, acceptance, sqlite_check, errors
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"闭环运行失败: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
