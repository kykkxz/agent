from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import CollectionPipeline
from .search import search
from .storage import read_jsonl, write_json


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="交通建设与运营安全知识采集插件")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect", help="执行一次采集")
    collect.add_argument("--manifest", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--offline", action="store_true", help="仅处理本地来源")
    status = subparsers.add_parser("status", help="显示最近一次运行摘要")
    status.add_argument("--output", type=Path, required=True)
    query = subparsers.add_parser("search", help="检索首轮知识库")
    query.add_argument("--output", type=Path, required=True)
    query.add_argument("--query", required=True)
    query.add_argument("--limit", type=int, default=5)
    evaluate = subparsers.add_parser("evaluate", help="运行固定问题验收")
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--questions", type=Path, required=True)
    return parser


def evaluate(output: Path, questions_path: Path) -> dict:
    entries = read_jsonl(output / "knowledge_base.jsonl")
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    results = []
    hits = 0
    citation_hits = 0
    for item in questions:
        matches = search(entries, item["question"], 5)
        title_terms = item.get("expected_title_terms", [])
        expect_covered = item.get("expect_covered", True)
        if expect_covered:
            hit = any(all(term in match["topic"] for term in title_terms) for match in matches) if title_terms else bool(matches)
            citation = bool(matches) and all(match.get("citations") for match in matches)
        else:
            hit = not matches
            citation = not matches
        hits += int(hit)
        citation_hits += int(citation)
        results.append({"id": item["id"], "question": item["question"], "hit": hit,
                        "expect_covered": expect_covered, "citation_complete": citation,
                        "top_results": matches})
    report = {
        "questions": len(questions), "top5_hits": hits,
        "top5_hit_rate": hits / max(len(questions), 1),
        "citation_complete_rate": citation_hits / max(len(questions), 1),
        "results": results,
    }
    write_json(output / "reports" / "acceptance_report.json", report)
    lines = ["# 固定问题检索验收报告", "", f"- 问题数：{len(questions)}",
             f"- Top 5 命中率：{report['top5_hit_rate']:.1%}",
             f"- 返回结果引用完整率：{report['citation_complete_rate']:.1%}", "",
             "未命中的问题表示当前首轮知识库缺少依据，不以猜测结果补齐。", ""]
    (output / "reports" / "acceptance_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    if args.command == "collect":
        print(json.dumps(
            CollectionPipeline(args.manifest, args.output).run(offline=args.offline),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if args.command == "status":
        path = args.output / "reports" / "run_summary.json"
        if not path.exists():
            print("尚无采集结果", file=sys.stderr)
            return 1
        print(path.read_text(encoding="utf-8"))
        return 0
    if args.command == "search":
        entries = read_jsonl(args.output / "knowledge_base.jsonl")
        matches = search(entries, args.query, args.limit)
        print(json.dumps(matches or {"status": "未收录或缺少依据", "results": []}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "evaluate":
        report = evaluate(args.output, args.questions)
        summary = {
            "questions": report["questions"],
            "top5_hits": report["top5_hits"],
            "top5_hit_rate": report["top5_hit_rate"],
            "citation_complete_rate": report["citation_complete_rate"],
            "report": str(args.output / "reports" / "acceptance_report.json"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
