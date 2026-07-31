from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

from flask import Flask
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from app import create_app

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
MAX_RESPONSE_CHARS = 20_000


@dataclass
class RequestSpec:
    method: str
    path: str
    json_body: Any | None = None
    query: dict[str, str] = field(default_factory=dict)
    form: dict[str, str] = field(default_factory=dict)
    file_path: Path | None = None
    file_field: str = "file"
    headers: dict[str, str] = field(default_factory=dict)
    use_auth: bool = True


@dataclass
class RequestRecord:
    method: str
    path: str
    status: int
    elapsed_ms: float
    message: str


def _key_value(value: str, option: str) -> tuple[str, str]:
    key, separator, item = value.partition("=")
    if not separator or not key:
        raise ValueError(f"{option} 需要使用 key=value 格式")
    return key, item


def parse_request_tokens(tokens: list[str]) -> RequestSpec:
    if len(tokens) < 2:
        raise ValueError("用法: request METHOD PATH [options]")

    method = tokens[0].upper()
    if method not in METHODS:
        raise ValueError(f"不支持的 HTTP 方法: {method}")

    spec = RequestSpec(method=method, path=tokens[1])
    index = 2
    while index < len(tokens):
        option = tokens[index]
        if option == "--json":
            index += 1
            if index >= len(tokens):
                raise ValueError("--json 缺少 JSON 内容")
            try:
                spec.json_body = json.loads(tokens[index])
            except json.JSONDecodeError as error:
                raise ValueError(f"JSON 无效: {error.msg}") from error
        elif option == "--query":
            index += 1
            if index >= len(tokens):
                raise ValueError("--query 缺少 key=value")
            key, value = _key_value(tokens[index], "--query")
            spec.query[key] = value
        elif option == "--form":
            index += 1
            if index >= len(tokens):
                raise ValueError("--form 缺少 key=value")
            key, value = _key_value(tokens[index], "--form")
            spec.form[key] = value
        elif option == "--file":
            index += 1
            if index >= len(tokens):
                raise ValueError("--file 缺少文件路径")
            spec.file_path = Path(tokens[index]).expanduser()
        elif option == "--file-field":
            index += 1
            if index >= len(tokens):
                raise ValueError("--file-field 缺少字段名")
            spec.file_field = tokens[index]
        elif option == "--header":
            index += 1
            if index >= len(tokens):
                raise ValueError("--header 缺少 key=value")
            key, value = _key_value(tokens[index], "--header")
            spec.headers[key] = value
        elif option == "--no-auth":
            spec.use_auth = False
        else:
            raise ValueError(f"未知选项: {option}")
        index += 1

    if spec.json_body is not None and (spec.form or spec.file_path):
        raise ValueError("--json 不能与 --form 或 --file 同时使用")
    if spec.path.startswith("http://") or spec.path.startswith("https://"):
        raise ValueError("终端只支持当前 Flask 应用内的路径，例如 /api/v1/auth/me")
    if not spec.path.startswith("/"):
        spec.path = "/" + spec.path
    return spec


def _route_rows(app: Flask) -> list[tuple[str, str, str]]:
    rows = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        methods = ", ".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        rows.append((methods, rule.rule, rule.endpoint))
    return sorted(rows, key=lambda row: row[1])


class DebugTerminal:
    def __init__(self, app: Flask, console: Console | None = None) -> None:
        self.app = app
        self.client = app.test_client()
        self.console = console or Console()
        self.token: str | None = None
        self.user: dict[str, Any] | None = None
        self.history: list[RequestRecord] = []
        self.routes = _route_rows(app)

    def run(self) -> None:
        self._show_banner()
        while True:
            try:
                command = Prompt.ask(
                    Text("debug", style="bold cyan"),
                    default="help",
                    console=self.console,
                )
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]已退出。[/dim]")
                return
            if self.execute_command(command):
                return

    def execute_command(self, command: str) -> bool:
        try:
            tokens = shlex.split(command)
        except ValueError as error:
            self.console.print(f"[red]命令解析失败:[/red] {error}")
            return False
        if not tokens:
            return False

        name, args = tokens[0].lower(), tokens[1:]
        try:
            if name in {"exit", "quit", "q"}:
                self.console.print("[dim]已退出。[/dim]")
                return True
            if name in {"help", "?"}:
                self._show_help(args[0] if args else None)
            elif name in {"routes", "route"}:
                self._show_routes(" ".join(args))
            elif name in {"request", "req"}:
                self._request(args)
            elif name == "login":
                self._login(args)
            elif name in {"whoami", "me"}:
                self._request(["GET", "/api/v1/auth/me"])
            elif name == "logout":
                self._logout()
            elif name == "token":
                self._set_token(args)
            elif name == "history":
                self._show_history()
            elif name == "clear":
                self.console.clear()
            else:
                self.console.print(
                    f"[yellow]未知命令:[/yellow] {name}，输入 help 查看帮助。"
                )
        except (ValueError, OSError) as error:
            self.console.print(f"[red]操作失败:[/red] {error}")
        return False

    def _show_banner(self) -> None:
        self.console.print(
            Panel.fit(
                "[bold white]保险精准营销系统[/bold white]\n"
                "[cyan]Flask 后端交互调试终端[/cyan]\n\n"
                "输入 [bold]help[/bold] 查看命令，输入 [bold]routes[/bold] 浏览接口。",
                border_style="cyan",
                title="Rich Debug Console",
            )
        )
        self._show_session()

    def _show_help(self, command: str | None) -> None:
        if command in {"request", "req"}:
            self.console.print(
                Panel(
                    "request METHOD PATH [--json JSON] [--query key=value] [--form key=value] "
                    "[--file path] [--file-field name] [--header key=value] [--no-auth]\n\n"
                    '例: request POST /api/v1/auth/login --json \'{"username":"admin",'
                    '"password":"admin123"}\'\n'
                    "例: request GET /api/v1/data/customers --query page=1 --query per_page=5\n"
                    "例: request POST /api/v1/data/upload --file data.xlsx",
                    title="request",
                    border_style="blue",
                )
            )
            return

        table = Table(title="可用命令", show_header=True, header_style="bold cyan")
        table.add_column("命令", style="green", no_wrap=True)
        table.add_column("作用")
        rows = [
            (
                "login [username] [password]",
                "登录并自动保存 JWT；不传密码时安全地交互输入",
            ),
            (
                "request / req",
                "调用当前 Flask 后端，支持 JSON、查询参数、表单、文件和请求头",
            ),
            ("routes [filter]", "列出接口路由，可按路径或 endpoint 过滤"),
            ("whoami / me", "调用当前用户接口"),
            ("token JWT", "手动设置 Bearer Token，便于复现已有会话"),
            ("logout", "调用登出接口并清除本地 Token"),
            ("history", "查看最近请求摘要"),
            ("clear", "清理终端画面"),
            ("help request", "查看 request 的完整参数格式"),
            ("quit / exit / q", "退出终端"),
        ]
        for name, description in rows:
            table.add_row(name, description)
        self.console.print(table)

    def _show_routes(self, keyword: str) -> None:
        table = Table(title="Flask 路由", header_style="bold cyan", show_lines=False)
        table.add_column("Method", style="green", no_wrap=True)
        table.add_column("Path", style="white")
        table.add_column("Endpoint", style="dim")
        visible = [
            row
            for row in self.routes
            if not keyword or keyword.lower() in " ".join(row).lower()
        ]
        for methods, path, endpoint in visible:
            table.add_row(methods, path, endpoint)
        self.console.print(table)
        self.console.print(f"[dim]共 {len(visible)} 条路由[/dim]")

    def _login(self, args: list[str]) -> None:
        username = (
            args[0]
            if args
            else Prompt.ask("用户名", default="admin", console=self.console)
        )
        password = (
            args[1]
            if len(args) > 1
            else Prompt.ask("密码", password=True, console=self.console)
        )
        if len(args) > 2:
            raise ValueError("login 最多接受 username 和 password 两个参数")
        response = self._send(
            RequestSpec(
                method="POST",
                path="/api/v1/auth/login",
                json_body={"username": username, "password": password},
                use_auth=False,
            )
        )
        payload = response.get_json(silent=True) or {}
        data = payload.get("data") if isinstance(payload, dict) else None
        if response.status_code < 400 and isinstance(data, dict):
            self.token = data.get("access_token")
            self.user = data.get("user")
            self._show_session()

    def _logout(self) -> None:
        if self.token:
            self._request(["POST", "/api/v1/auth/logout"])
        self.token = None
        self.user = None
        self._show_session()

    def _set_token(self, args: list[str]) -> None:
        if len(args) != 1:
            raise ValueError("用法: token JWT")
        self.token = args[0]
        self.user = None
        self.console.print("[green]已设置 Bearer Token。[/green]")
        self._show_session()

    def _request(self, args: list[str]) -> None:
        if not args:
            method = Prompt.ask(
                "Method", choices=list(METHODS), default="GET", console=self.console
            )
            path = Prompt.ask("Path", default="/api/v1/auth/me", console=self.console)
            args = [method, path]
            body = Prompt.ask("JSON (留空跳过)", default="", console=self.console)
            if body:
                args.extend(["--json", body])
        spec = parse_request_tokens(args)
        self._send(spec)

    def _send(self, spec: RequestSpec):
        query = dict(parse_qsl(spec.path.partition("?")[2], keep_blank_values=True))
        path = spec.path.partition("?")[0]
        query.update(spec.query)
        headers = dict(spec.headers)
        if spec.use_auth and self.token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.token}"

        request_kwargs: dict[str, Any] = {
            "method": spec.method,
            "path": path,
            "headers": headers,
        }
        if query:
            request_kwargs["query_string"] = query
        if spec.json_body is not None:
            request_kwargs["json"] = spec.json_body
        elif spec.file_path is not None:
            if not spec.file_path.is_file():
                raise FileNotFoundError(f"文件不存在: {spec.file_path}")
            request_kwargs["data"] = {
                **spec.form,
                spec.file_field: (spec.file_path.open("rb"), spec.file_path.name),
            }
        elif spec.form:
            request_kwargs["data"] = spec.form

        started = time.perf_counter()
        try:
            response = self.client.open(**request_kwargs)
        finally:
            upload = request_kwargs.get("data", {}).get(spec.file_field)
            if isinstance(upload, tuple) and hasattr(upload[0], "close"):
                upload[0].close()
        elapsed_ms = (time.perf_counter() - started) * 1000
        payload = response.get_json(silent=True)
        message = payload.get("message", "") if isinstance(payload, dict) else ""
        self.history.append(
            RequestRecord(
                spec.method, spec.path, response.status_code, elapsed_ms, str(message)
            )
        )
        self._show_response(spec, response, elapsed_ms)
        return response

    def _show_response(
        self, spec: RequestSpec, response: Any, elapsed_ms: float
    ) -> None:
        status_style = "green" if response.status_code < 400 else "red"
        self.console.print(
            f"[{status_style}]{response.status_code}[/{status_style}] "
            f"[bold]{spec.method}[/bold] {spec.path} [dim]{elapsed_ms:.1f} ms[/dim]"
        )
        self.console.print(
            f"[dim]Content-Type: {response.content_type or 'unknown'}[/dim]"
        )
        payload = response.get_json(silent=True)
        if payload is not None:
            rendered = json.dumps(payload, ensure_ascii=False, indent=2)
            if len(rendered) > MAX_RESPONSE_CHARS:
                rendered = (
                    rendered[:MAX_RESPONSE_CHARS] + "\n... response truncated ..."
                )
            self.console.print(JSON(rendered))
            return
        if response.data:
            if response.content_type and response.content_type.startswith("text/"):
                body = response.get_data(as_text=True)
                self.console.print(body[:MAX_RESPONSE_CHARS])
            else:
                self.console.print(
                    f"[dim]二进制响应: {len(response.data):,} bytes[/dim]"
                )
        else:
            self.console.print("[dim]空响应体[/dim]")

    def _show_session(self) -> None:
        if self.token:
            username = self.user.get("username") if self.user else "token session"
            role = self.user.get("role") if self.user else "unknown role"
            self.console.print(
                f"[green]会话:[/green] {username} ({role}) · Bearer Token 已启用"
            )
        else:
            self.console.print("[yellow]会话:[/yellow] 未登录 · 受保护接口将返回 401")

    def _show_history(self) -> None:
        if not self.history:
            self.console.print("[dim]暂无请求记录。[/dim]")
            return
        table = Table(title="最近请求", header_style="bold cyan")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Method", style="green")
        table.add_column("Path")
        table.add_column("Status", justify="right")
        table.add_column("Time", justify="right")
        table.add_column("Message")
        for index, record in enumerate(
            self.history[-20:], start=max(1, len(self.history) - 19)
        ):
            status_style = "green" if record.status < 400 else "red"
            table.add_row(
                str(index),
                record.method,
                record.path,
                f"[{status_style}]{record.status}[/{status_style}]",
                f"{record.elapsed_ms:.1f} ms",
                record.message,
            )
        self.console.print(table)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="保险精准营销系统 Rich 后端调试终端")
    parser.add_argument(
        "--command",
        action="append",
        help="启动后执行命令，可重复传入；适合脚本化冒烟测试",
    )
    parser.add_argument("--no-color", action="store_true", help="关闭 Rich 颜色")
    args = parser.parse_args(argv)

    console = Console(color_system=None if args.no_color else "auto")
    try:
        terminal = DebugTerminal(create_app(), console)
        if args.command:
            for command in args.command:
                if terminal.execute_command(command):
                    break
            return 0
        terminal.run()
    except KeyboardInterrupt:
        console.print("\n[dim]已退出。[/dim]")
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        console.print_exception(show_locals=False)
        console.print(f"[red]启动失败:[/red] {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
