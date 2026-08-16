from __future__ import annotations

import argparse
import json
from pathlib import Path


def clean_text(text: str, max_chars: int | None = None) -> str:
    normalized = " ".join(str(text or "").split())
    if max_chars is not None and len(normalized) > max_chars:
        return normalized[: max_chars - 1] + "…"
    return normalized


def write_markdown(report: dict, path: Path) -> None:
    lines: list[str] = []
    lines.append("# RAG 模拟检索报告（人类可读版）")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **状态**：{report['status']}")
    lines.append(f"- **时间（UTC）**：{report['created_at']}")
    lines.append(
        f"- **设备**：{report['device']}（CUDA可用: {report['cuda_available']}）"
    )
    lines.append(f"- **候选池**：{report['pool_size']} 条正式证据")
    lines.append(
        f"- **命中率**：{report['hits']}/{report['questions']}（{report['hit_rate']:.1%}）"
    )
    lines.append(f"- **总耗时**：{report['total_elapsed_ms']} ms")
    params = report.get("params", {})
    lines.append(
        "- **参数**：" +
        f"limit={params.get('limit')}, " +
        f"retrieval_top_k={params.get('retrieval_top_k')}, " +
        f"rrf_top_k={params.get('rrf_top_k')}"
    )
    lines.append("")
    lines.append("## 一览表")
    lines.append("")
    lines.append("| 编号 | 类别 | 结果 | 耗时 | 问题 | Top1 标题 | Top1 定位 |")
    lines.append("| --- | --- | --- | ---: | --- | --- | --- |")
    for item in report["results"]:
        top = item["top_results"][0] if item["top_results"] else {}
        hit = "✅ 命中" if item["hit"] else "❌ 未命中"
        lines.append(
            "| {id} | {category} | {hit} | {elapsed} ms | {query} | {title} | {locator} |".format(
                id=item["id"],
                category=item["category"],
                hit=hit,
                elapsed=item["elapsed_ms"],
                query=str(item["query"]).replace("|", "\\|"),
                title=str(top.get("title", "（空）")).replace("|", "\\|"),
                locator=str(top.get("locator", "-")).replace("|", "\\|"),
            )
        )
    lines.append("")
    lines.append("## 逐条详情")
    lines.append("")
    for item in report["results"]:
        status = "✅ 命中" if item["hit"] else "❌ 未命中"
        lines.append(f"### {item['id']} · {item['category']} · {status}")
        lines.append("")
        lines.append(f"- **模拟命令**：`{item['command']}`")
        lines.append(f"- **查询问题**：{item['query']}")
        lines.append(f"- **检索耗时**：{item['elapsed_ms']} ms")
        lines.append(f"- **返回条数**：{item['result_count']}")
        terms = item.get("expected_title_terms") or []
        if terms:
            lines.append("- **期望标题含**：" + "、".join(terms))
        if item.get("expect_empty"):
            lines.append("- **期望结果**：空结果（负例）")
        lines.append("")
        if not item["top_results"]:
            lines.append("> 无检索结果（符合未公开/无覆盖策略时属正常）")
            lines.append("")
            continue
        for rank, row in enumerate(item["top_results"], start=1):
            ranks = row.get("retrieval_ranks") or {}
            rank_text = ", ".join(f"{name}#{pos}" for name, pos in ranks.items()) or "-"
            lines.append(f"#### 结果 {rank}")
            lines.append("")
            lines.append(f"- **标题**：{row['title']}")
            lines.append(f"- **类型**：{row['document_type']}")
            lines.append(f"- **定位**：{row['locator']}")
            lines.append(
                f"- **评分**：rerank `{row['rerank_score']}` · rrf `{row['rrf_score']}`"
            )
            lines.append(f"- **召回路径**：{rank_text}")
            lines.append(f"- **证据ID**：`{row['evidence_id']}`")
            lines.append(
                f"- **层级**：{row.get('publication_layer', '-')} / {row.get('review_status', '-')}"
            )
            lines.append(f"- **来源**：{row['source_uri']}")
            lines.append(f"- **正文摘要**：{clean_text(row['text'], 220)}")
            lines.append("")
        lines.append("<details>")
        lines.append("<summary>展开查看 Context Pack（可直接给大模型）</summary>")
        lines.append("")
        lines.append("```text")
        lines.append(str(item.get("context") or "（空）"))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    lines.append("## 机器可读文件")
    lines.append("")
    lines.append("- 完整 JSON：同目录 `rag_simulate_20_report.json`")
    lines.append("- 纯文本：同目录 `rag_simulate_20_report.txt`")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_plaintext(report: dict, path: Path) -> None:
    lines: list[str] = []
    lines.append("RAG 模拟检索报告（人类可读）")
    lines.append("=" * 72)
    lines.append(f"状态      : {report['status']}")
    lines.append(f"时间(UTC) : {report['created_at']}")
    lines.append(f"设备      : {report['device']}")
    lines.append(f"候选池    : {report['pool_size']}")
    lines.append(
        f"命中率    : {report['hits']}/{report['questions']} ({report['hit_rate']:.1%})"
    )
    lines.append(f"总耗时    : {report['total_elapsed_ms']} ms")
    lines.append("")
    for item in report["results"]:
        status = "命中" if item["hit"] else "未命中"
        lines.append("-" * 72)
        lines.append(
            f"{item['id']} | {item['category']} | {status} | {item['elapsed_ms']} ms"
        )
        lines.append(f"命令: {item['command']}")
        lines.append(f"问题: {item['query']}")
        if not item["top_results"]:
            lines.append("结果: （空）")
            lines.append("")
            continue
        for rank, row in enumerate(item["top_results"], start=1):
            lines.append(
                f"  [{rank}] {row['title']}  |  {row['locator']}  |  score={row['rerank_score']}"
            )
            lines.append(
                f"      类型: {row['document_type']}  ID: {row['evidence_id']}"
            )
            lines.append(f"      来源: {row['source_uri']}")
            lines.append(f"      摘要: {clean_text(row['text'], 160)}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="把 simulate JSON 渲染成人类可读报告")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_root / "data" / "reports" / "rag_simulate_20_report.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=project_root / "data" / "reports" / "rag_simulate_20_report.md",
    )
    parser.add_argument(
        "--plaintext",
        type=Path,
        default=project_root / "data" / "reports" / "rag_simulate_20_report.txt",
    )
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(report, args.markdown)
    write_plaintext(report, args.plaintext)
    print(f"[OK] Markdown -> {args.markdown}")
    print(f"[OK] 纯文本  -> {args.plaintext}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
