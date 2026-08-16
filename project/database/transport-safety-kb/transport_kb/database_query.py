from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

DEFAULT_DATABASE = Path("data/transport_safety_kb.sqlite3")
MAX_LIMIT = 500


class QueryError(ValueError):
    """An expected query or input error that should be shown without a traceback."""


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def open_read_only(database: Path) -> sqlite3.Connection:
    if not database.is_file():
        raise QueryError(f"数据库不存在：{database}")
    uri = f"file:{database.resolve().as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise QueryError(f"无法打开数据库：{exc}") from exc
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def list_tables(
    connection: sqlite3.Connection, include_internal: bool = False
) -> list[dict[str, Any]]:
    records = connection.execute(
        """
        SELECT name, type, sql
        FROM sqlite_master
        WHERE type IN ('table', 'view')
        ORDER BY name
        """
    ).fetchall()
    results = []
    for record in records:
        name = record["name"]
        definition = record["sql"] or ""
        internal = name.startswith(("sqlite_", "knowledge_fts"))
        if internal and not include_internal:
            continue
        quoted = _quote_identifier(name)
        try:
            row_count = connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
        except sqlite3.Error:
            row_count = None
        results.append(
            {
                "name": name,
                "type": record["type"],
                "row_count": row_count,
                "internal": internal,
                "virtual": "CREATE VIRTUAL TABLE" in definition.upper(),
            }
        )
    return results


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        )
    }


def _require_table(connection: sqlite3.Connection, table: str) -> None:
    if table not in _table_names(connection):
        available = ", ".join(item["name"] for item in list_tables(connection))
        raise QueryError(f"表不存在：{table}\n可用业务表：{available}")


def table_schema(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    _require_table(connection, table)
    rows = connection.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()
    return [
        {
            "position": row["cid"],
            "name": row["name"],
            "type": row["type"],
            "not_null": bool(row["notnull"]),
            "default": row["dflt_value"],
            "primary_key": bool(row["pk"]),
        }
        for row in rows
    ]


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {item["name"] for item in table_schema(connection, table)}


def _parse_filters(
    connection: sqlite3.Connection, table: str, filters: Sequence[str]
) -> tuple[list[str], list[str]]:
    columns = _column_names(connection, table)
    clauses: list[str] = []
    values: list[str] = []
    for item in filters:
        if "=" not in item:
            raise QueryError(f"筛选条件格式错误：{item}；应为 字段=值")
        column, value = item.split("=", 1)
        column = column.strip()
        if column not in columns:
            raise QueryError(f"表 {table} 中不存在字段：{column}")
        clauses.append(f"{_quote_identifier(column)} = ?")
        values.append(value)
    return clauses, values


def read_rows(
    connection: sqlite3.Connection,
    table: str,
    limit: int,
    offset: int,
    filters: Sequence[str] = (),
) -> list[dict[str, Any]]:
    _require_table(connection, table)
    clauses, values = _parse_filters(connection, table, filters)
    sql = f"SELECT * FROM {_quote_identifier(table)}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " LIMIT ? OFFSET ?"
    try:
        rows = connection.execute(sql, [*values, limit, offset]).fetchall()
    except sqlite3.Error as exc:
        raise QueryError(f"读取表 {table} 失败：{exc}") from exc
    return [dict(row) for row in rows]


def search_tables(
    connection: sqlite3.Connection,
    keyword: str,
    limit: int,
    table: str | None = None,
    include_internal: bool = False,
) -> list[dict[str, Any]]:
    if not keyword:
        raise QueryError("关键词不能为空")
    if table:
        _require_table(connection, table)
        tables = [table]
    else:
        tables = [
            item["name"] for item in list_tables(connection, include_internal=include_internal)
        ]

    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    results: list[dict[str, Any]] = []
    for table_name in tables:
        schema = table_schema(connection, table_name)
        searchable = [
            item["name"]
            for item in schema
            if not item["type"] or any(
                marker in item["type"].upper() for marker in ("CHAR", "CLOB", "TEXT")
            )
        ]
        if not searchable:
            continue
        predicates = [
            f"{_quote_identifier(column)} LIKE ? ESCAPE '\\'" for column in searchable
        ]
        remaining = limit - len(results)
        sql = (
            f"SELECT * FROM {_quote_identifier(table_name)} WHERE "
            + " OR ".join(predicates)
            + " LIMIT ?"
        )
        try:
            rows = connection.execute(sql, [pattern] * len(searchable) + [remaining]).fetchall()
        except sqlite3.Error as exc:
            raise QueryError(f"检索表 {table_name} 失败：{exc}") from exc
        results.extend({"table": table_name, "row": dict(row)} for row in rows)
        if len(results) >= limit:
            break
    return results


def _bounded_limit(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if not 1 <= number <= MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"必须在 1 到 {MAX_LIMIT} 之间")
    return number


def _non_negative(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("不能小于 0")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="只读检索交通安全知识库中的各类 SQLite 表",
        epilog=(
            "示例：\n"
            "  python query_database.py\n"
            "  python query_database.py tables\n"
            "  python query_database.py schema --table documents\n"
            "  python query_database.py rows --table documents --limit 10\n"
            "  python query_database.py search --keyword 隧道事故"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--database", type=Path, default=DEFAULT_DATABASE, help=f"数据库路径（默认：{DEFAULT_DATABASE}）"
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出，便于脚本处理")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("interactive", help="启动 Rich 交互检索界面")

    tables = subparsers.add_parser("tables", help="列出表和记录数")
    tables.add_argument("--include-internal", action="store_true", help="包含 FTS 和 SQLite 内部表")

    schema = subparsers.add_parser("schema", help="查看指定表的字段结构")
    schema.add_argument("--table", required=True, help="表名")

    rows = subparsers.add_parser("rows", help="分页查看指定表的数据")
    rows.add_argument("--table", required=True, help="表名")
    rows.add_argument("--limit", type=_bounded_limit, default=20, help="返回条数（默认：20）")
    rows.add_argument("--offset", type=_non_negative, default=0, help="跳过条数（默认：0）")
    rows.add_argument(
        "--where", action="append", default=[], metavar="字段=值", help="精确筛选，可重复使用"
    )

    search = subparsers.add_parser("search", help="跨表或在指定表中检索关键词")
    search.add_argument("--keyword", required=True, help="要检索的关键词")
    search.add_argument("--table", help="仅检索指定表；默认检索全部业务表")
    search.add_argument("--limit", type=_bounded_limit, default=20, help="返回条数（默认：20）")
    search.add_argument("--include-internal", action="store_true", help="检索 FTS 和 SQLite 内部表")
    return parser


def _cell_text(value: Any, width: int = 60) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        text = f"<BLOB {len(value)} bytes>"
    else:
        text = str(value).replace("\r", " ").replace("\n", " ")
    return text if len(text) <= width else text[: width - 3] + "..."


def _print_table(rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        print("未找到记录")
        return
    columns = list(rows[0])
    widths = {
        column: min(60, max(len(column), *[len(_cell_text(row.get(column))) for row in rows]))
        for column in columns
    }
    print(" | ".join(column.ljust(widths[column]) for column in columns))
    print("-+-".join("-" * widths[column] for column in columns))
    for row in rows:
        print(" | ".join(_cell_text(row.get(column)).ljust(widths[column]) for column in columns))


def _print_search_results(results: Sequence[dict[str, Any]]) -> None:
    if not results:
        print("未找到记录")
        return
    for index, result in enumerate(results, 1):
        print(f"[{index}] 表：{result['table']}")
        _print_table([result["row"]])
        print()


def _rich_value(value: Any, width: int = 80) -> Text:
    return Text(_cell_text(value, width), overflow="ellipsis", no_wrap=False)


def _rich_table(
    rows: Sequence[dict[str, Any]], title: str | None = None, columns: Sequence[str] | None = None
) -> Table:
    selected = list(columns or (list(rows[0]) if rows else []))
    table = Table(title=title, box=box.SIMPLE_HEAVY, header_style="bold cyan", show_lines=False)
    for column in selected:
        table.add_column(column, overflow="ellipsis")
    for row in rows:
        table.add_row(*[_rich_value(row.get(column)) for column in selected])
    return table


def _show_rich_table(
    console: Console,
    rows: Sequence[dict[str, Any]],
    title: str | None = None,
    columns: Sequence[str] | None = None,
) -> None:
    if not rows:
        console.print("[yellow]未找到记录[/yellow]")
        return
    console.print(_rich_table(rows, title, columns))


def _summary_columns(rows: Sequence[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    available = list(rows[0])
    preferred = [
        available[0],
        "title",
        "topic",
        "document_type",
        "publisher",
        "stage",
        "review_status",
        "locator",
        "completed_at",
        "key",
        "value",
    ]
    selected: list[str] = []
    for column in preferred + available:
        if column in available and column not in selected:
            selected.append(column)
        if len(selected) == 6:
            break
    return selected


def _show_record(console: Console, row: dict[str, Any], title: str) -> None:
    details = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    details.add_column("字段", style="bold cyan", no_wrap=True)
    details.add_column("值", overflow="fold")
    for key, value in row.items():
        details.add_row(key, _rich_value(value, 500))
    console.print(Panel(details, title=title, border_style="cyan"))


def _choose_table(console: Console, connection: sqlite3.Connection) -> str | None:
    tables = list_tables(connection)
    display = [
        {"序号": index, "表名": item["name"], "记录数": item["row_count"]}
        for index, item in enumerate(tables, 1)
    ]
    _show_rich_table(console, display, "业务表")
    choice = IntPrompt.ask("选择表（0 返回）", choices=[str(i) for i in range(len(tables) + 1)])
    return None if choice == 0 else tables[choice - 1]["name"]


def _browse_table(
    console: Console,
    connection: sqlite3.Connection,
    table: str,
    filters: Sequence[str] = (),
    page_size: int = 10,
) -> None:
    offset = 0
    while True:
        rows = read_rows(connection, table, page_size, offset, filters)
        if rows:
            display = [{"序号": offset + index, **row} for index, row in enumerate(rows, 1)]
            columns = ["序号", *_summary_columns(rows)]
            _show_rich_table(console, display, f"{table} · 第 {offset // page_size + 1} 页", columns)
        else:
            console.print("[yellow]当前页没有记录[/yellow]")

        choices = ["n", "b"]
        if offset:
            choices.append("p")
        if rows:
            choices.append("d")
        action = Prompt.ask(
            "操作：[bold]n[/bold] 下一页  [bold]p[/bold] 上一页  "
            "[bold]d[/bold] 查看详情  [bold]b[/bold] 返回",
            choices=choices,
            default="b",
        )
        if action == "b":
            return
        if action == "n":
            offset += page_size
        elif action == "p":
            offset = max(0, offset - page_size)
        elif action == "d":
            number = IntPrompt.ask(
                "记录序号",
                choices=[str(index) for index in range(offset + 1, offset + len(rows) + 1)],
            )
            _show_record(console, rows[number - offset - 1], f"{table} #{number}")


def _matching_snippet(row: dict[str, Any], keyword: str, width: int = 90) -> str:
    for value in row.values():
        text = str(value).replace("\r", " ").replace("\n", " ")
        position = text.lower().find(keyword.lower())
        if position >= 0:
            start = max(0, position - 25)
            end = min(len(text), position + len(keyword) + width - 25)
            prefix = "..." if start else ""
            suffix = "..." if end < len(text) else ""
            return prefix + text[start:end] + suffix
    return ""


def _show_search_results(
    console: Console,
    results: Sequence[dict[str, Any]],
    keyword: str,
    prompt_for_details: bool = False,
) -> None:
    display = []
    for index, result in enumerate(results, 1):
        row = result["row"]
        display.append(
            {
                "序号": index,
                "表名": result["table"],
                "标题/主题": row.get("title") or row.get("topic") or row.get("key") or "",
                "命中内容": _matching_snippet(row, keyword),
            }
        )
    _show_rich_table(console, display, f"检索结果 · {keyword}")
    if not results or not prompt_for_details:
        return
    while True:
        choice = IntPrompt.ask(
            "输入序号查看详情（0 返回）", choices=[str(i) for i in range(len(results) + 1)]
        )
        if choice == 0:
            return
        result = results[choice - 1]
        _show_record(console, result["row"], f"{result['table']} #{choice}")


def run_interactive(
    connection: sqlite3.Connection,
    database: Path,
    console: Console | None = None,
) -> int:
    console = console or Console()
    tables = list_tables(connection)
    console.print(
        Panel(
            f"[bold]交通建设与运营安全知识库[/bold]\n"
            f"[dim]{database.resolve()}[/dim]\n"
            f"业务表 {len(tables)} 张 · SQLite 只读模式",
            border_style="cyan",
        )
    )
    while True:
        menu = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        menu.add_column("序号", style="bold cyan", justify="right")
        menu.add_column("功能")
        for number, label in (
            ("1", "浏览数据表"),
            ("2", "关键词检索"),
            ("3", "查看表结构"),
            ("4", "按字段精确筛选"),
            ("5", "查看表与记录数"),
            ("0", "退出"),
        ):
            menu.add_row(number, label)
        console.print(menu)
        choice = Prompt.ask("选择功能", choices=["0", "1", "2", "3", "4", "5"])
        if choice == "0":
            console.print("[dim]已退出[/dim]")
            return 0
        if choice == "1":
            table = _choose_table(console, connection)
            if table:
                page_size = IntPrompt.ask("每页记录数", default=10)
                if not 1 <= page_size <= 50:
                    console.print("[yellow]每页记录数应在 1 到 50 之间[/yellow]")
                    continue
                _browse_table(console, connection, table, page_size=page_size)
        elif choice == "2":
            keyword = Prompt.ask("关键词").strip()
            if not keyword:
                console.print("[yellow]关键词不能为空[/yellow]")
                continue
            scope = Prompt.ask("检索范围：1 全部业务表  2 指定表", choices=["1", "2"], default="1")
            table = _choose_table(console, connection) if scope == "2" else None
            if scope == "2" and table is None:
                continue
            results = search_tables(connection, keyword, limit=50, table=table)
            _show_search_results(console, results, keyword, prompt_for_details=True)
        elif choice == "3":
            table = _choose_table(console, connection)
            if table:
                _show_rich_table(console, table_schema(connection, table), f"{table} · 字段结构")
        elif choice == "4":
            table = _choose_table(console, connection)
            if not table:
                continue
            schema = table_schema(connection, table)
            columns = [item["name"] for item in schema]
            field_rows = [{"序号": index, "字段": name} for index, name in enumerate(columns, 1)]
            _show_rich_table(console, field_rows, f"{table} · 选择筛选字段")
            field_number = IntPrompt.ask(
                "字段序号", choices=[str(i) for i in range(1, len(columns) + 1)]
            )
            value = Prompt.ask("精确匹配值")
            _browse_table(console, connection, table, [f"{columns[field_number - 1]}={value}"])
        elif choice == "5":
            _show_rich_table(console, tables, "业务表概览")


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None and not sys.stdin.isatty():
        parser.print_help(sys.stderr)
        return 2
    try:
        with closing(open_read_only(args.database)) as connection:
            if args.command in (None, "interactive"):
                return run_interactive(connection, args.database)
            if args.command == "tables":
                result: Any = list_tables(connection, args.include_internal)
            elif args.command == "schema":
                result = table_schema(connection, args.table)
            elif args.command == "rows":
                result = read_rows(connection, args.table, args.limit, args.offset, args.where)
            elif args.command == "search":
                result = search_tables(
                    connection, args.keyword, args.limit, args.table, args.include_internal
                )
            else:
                parser.error(f"未知命令：{args.command}")
                return 2
    except QueryError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"数据库错误：{exc}", file=sys.stderr)
        return 1
    except EOFError:
        print("输入已结束，程序退出", file=sys.stderr)
        return 0
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        return 130

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.command == "search":
        _show_search_results(Console(), result, args.keyword)
    else:
        _show_rich_table(Console(), result)
    return 0
