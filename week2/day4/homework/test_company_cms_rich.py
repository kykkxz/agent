import json
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.orm import Session

from app_company_cms import ENGINE, News, app

console = Console()
BASE_URL = "http://127.0.0.1:5005"


def request_json(
    client: Any,
    method: str,
    path: str,
    command: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.open(path, method=method, json=body)
    result = response.get_json() or {}
    show_result(method, path, command, response.status_code, result)
    return result


def show_result(
    method: str,
    path: str,
    command: str,
    status_code: int,
    result: dict[str, Any],
) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("字段", style="cyan", no_wrap=True)
    table.add_column("内容", style="white")
    table.add_row("接口", f"{method} {path}")
    table.add_row("命令", command)
    table.add_row("状态码", str(status_code))

    console.print(Panel(table, title="使用的命令", border_style="blue"))
    console.print(
        Panel(
            JSON(json.dumps(result, ensure_ascii=False, indent=2)),
            title="返回的结果",
            border_style="green" if status_code < 400 else "red",
        )
    )
    console.print()


def show_menu() -> None:
    table = Table(title="公司 CMS 交互式接口测试", show_lines=True)
    table.add_column("编号", justify="center", style="cyan", no_wrap=True)
    table.add_column("功能", style="white")
    table.add_column("接口", style="green")
    table.add_row("1", "查看公司首页", "GET /")
    table.add_row("2", "查看新闻列表", "GET /api/news")
    table.add_row("3", "查看新闻详情", "GET /api/news/<id>")
    table.add_row("4", "管理员登录", "POST /admin/login")
    table.add_row("5", "发布新闻", "POST /admin/news")
    table.add_row("6", "删除新闻", "DELETE /admin/news/<id>")
    table.add_row("7", "查询数据库内容", "SQLite news 表")
    table.add_row("0", "退出", "-")
    console.print(table)


def build_post_command(path: str, body: dict[str, Any], with_cookie: bool = False) -> str:
    json_body = json.dumps(body, ensure_ascii=False)
    cookie = ' -b "session=<管理员登录后的 Cookie>"' if with_cookie else ""
    return f'curl -X POST {BASE_URL}{path} -H "Content-Type: application/json"{cookie} -d \'{json_body}\''


def build_delete_command(path: str) -> str:
    return f'curl -X DELETE {BASE_URL}{path} -b "session=<管理员登录后的 Cookie>"'


def handle_home(client: Any) -> None:
    request_json(client, "GET", "/", f"curl {BASE_URL}/")


def handle_list_news(client: Any) -> None:
    request_json(client, "GET", "/api/news", f"curl {BASE_URL}/api/news")


def handle_news_detail(client: Any) -> None:
    news_id = Prompt.ask("请输入新闻 ID", default="1")
    path = f"/api/news/{news_id}"
    request_json(client, "GET", path, f"curl {BASE_URL}{path}")


def handle_admin_login(client: Any) -> None:
    username = Prompt.ask("管理员用户名", default="admin")
    password = Prompt.ask("管理员密码", default="admin123", password=True)
    body = {
        "username": username,
        "password": password,
    }
    request_json(client, "POST", "/admin/login", build_post_command("/admin/login", body), body)


def handle_create_news(client: Any) -> None:
    title = Prompt.ask("新闻标题")
    content = Prompt.ask("新闻内容")
    category = Prompt.ask("新闻分类", default="公司公告")
    body = {
        "title": title,
        "content": content,
        "category": category,
    }
    request_json(
        client,
        "POST",
        "/admin/news",
        build_post_command("/admin/news", body, with_cookie=True),
        body,
    )


def handle_delete_news(client: Any) -> None:
    news_id = Prompt.ask("请输入要删除的新闻 ID")
    path = f"/admin/news/{news_id}"
    request_json(client, "DELETE", path, build_delete_command(path))


def handle_show_db_news(client: Any) -> None:
    limit = IntPrompt.ask("查看最近多少条数据库记录", default=20)

    with Session(ENGINE) as db_session:
        rows = db_session.scalars(
            select(News).order_by(News.published_at.desc(), News.id.desc()).limit(limit)
        ).all()

    if not rows:
        console.print(Panel("[yellow]数据库暂无新闻内容[/yellow]", title="cms.db"))
        console.print()
        return

    table = Table(title=f"cms.db news 表最近 {len(rows)} 条", show_lines=True)
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("发布时间", style="green", no_wrap=True)
    table.add_column("分类", style="magenta", no_wrap=True)
    table.add_column("标题", style="white")
    table.add_column("作者", style="blue", no_wrap=True)

    for row in rows:
        table.add_row(
            str(row.id),
            str(row.published_at),
            str(row.category),
            str(row.title),
            str(row.author),
        )

    console.print(table)
    console.print()


def main() -> None:
    console.print(Panel.fit("公司 CMS 交互式接口测试", style="bold magenta"))
    console.print("[dim]提示：本程序使用 Flask test client，不需要先启动服务器。[/dim]\n")

    client = app.test_client()
    actions = {
        "1": handle_home,
        "2": handle_list_news,
        "3": handle_news_detail,
        "4": handle_admin_login,
        "5": handle_create_news,
        "6": handle_delete_news,
        "7": handle_show_db_news,
    }

    while True:
        show_menu()
        choice = Prompt.ask("请选择操作", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="1")
        console.print()

        if choice == "0":
            console.print("[green]已退出测试程序[/green]")
            break

        actions[choice](client)


if __name__ == "__main__":
    main()
