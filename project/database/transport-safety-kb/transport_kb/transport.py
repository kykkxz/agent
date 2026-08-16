from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from .models import FetchResult


class CurlTransport:
    """Fetch public HTTP resources with the operating system TLS trust store."""

    def __init__(self, timeout_seconds: int = 45) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, uri: str, method: str = "GET", headers: dict[str, str] | None = None,
              body: str | None = None) -> FetchResult:
        parsed = urlparse(uri)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return FetchResult(uri, uri, 0, "", b"", "curl", "unsupported URI")

        with tempfile.TemporaryDirectory(prefix="transport-kb-") as temp_dir:
            body_path = Path(temp_dir) / "body.bin"
            header_path = Path(temp_dir) / "headers.txt"
            command = [
                "curl.exe", "--silent", "--show-error", "--location",
                "--compressed",
                "--max-time", str(self.timeout_seconds),
                "--retry", "2", "--retry-delay", "1", "--retry-all-errors",
                "--user-agent", "TransportSafetyKnowledgeCollector/0.1 (+public-research)",
                "--dump-header", str(header_path), "--output", str(body_path),
                "--write-out", "%{http_code}\n%{url_effective}\n%{content_type}",
            ]
            if method != "GET":
                command.extend(["--request", method])
            for name, value in (headers or {}).items():
                command.extend(["--header", f"{name}: {value}"])
            if body is not None:
                command.extend(["--data-raw", body])
            command.append(uri)
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    check=False,
                    timeout=self.timeout_seconds * 3 + 10,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return FetchResult(uri, uri, 0, "", b"", "curl", str(exc))

            lines = completed.stdout.decode("utf-8", errors="replace").splitlines()
            status = int(lines[0]) if lines and lines[0].isdigit() else 0
            final_uri = lines[1] if len(lines) > 1 else uri
            media_type = lines[2].split(";", 1)[0] if len(lines) > 2 else ""
            content = body_path.read_bytes() if body_path.exists() else b""
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            if completed.returncode != 0 and not error:
                error = f"curl exit code {completed.returncode}"
            return FetchResult(uri, final_uri, status, media_type, content, "curl", error)
