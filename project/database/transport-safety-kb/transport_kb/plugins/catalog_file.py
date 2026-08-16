from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import SourceCandidate
from ..transport import CurlTransport
from .base import SourcePlugin


class CatalogFilePlugin(SourcePlugin):
    """Load a generated, reviewable catalog of public source URLs."""

    plugin_name = "catalog_file_plugin"

    def __init__(self, project_root: Path, transport: CurlTransport) -> None:
        self.project_root = project_root.resolve()
        self.transport = transport

    def discover(self, config: dict[str, Any]) -> list[SourceCandidate]:
        configured_path = Path(config["path"])
        path = configured_path if configured_path.is_absolute() else self.project_root / configured_path
        if not path.is_file():
            if config.get("required", True):
                raise FileNotFoundError(f"generated source catalog does not exist: {path}")
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload["sources"] if isinstance(payload, dict) else payload
        return [SourceCandidate(plugin=self.plugin_name, **record) for record in records]

    def fetch(self, candidate: SourceCandidate):
        return self.transport.fetch(candidate.source_uri)
