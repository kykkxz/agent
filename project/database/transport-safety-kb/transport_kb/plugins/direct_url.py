from __future__ import annotations

from typing import Any

from ..models import SourceCandidate
from ..transport import CurlTransport
from .base import SourcePlugin


class DirectUrlPlugin(SourcePlugin):
    plugin_name = "direct_url_plugin"

    def __init__(self, transport: CurlTransport) -> None:
        self.transport = transport

    def discover(self, config: dict[str, Any]) -> list[SourceCandidate]:
        return [SourceCandidate(plugin=self.plugin_name, **item) for item in config.get("sources", [])]

    def fetch(self, candidate: SourceCandidate):
        return self.transport.fetch(candidate.source_uri)

