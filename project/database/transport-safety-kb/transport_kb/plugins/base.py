from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import FetchResult, SourceCandidate


class SourcePlugin(ABC):
    plugin_name: str

    @abstractmethod
    def discover(self, config: dict[str, Any]) -> list[SourceCandidate]:
        """Discover new or updated source documents."""

    @abstractmethod
    def fetch(self, candidate: SourceCandidate) -> FetchResult:
        """Fetch the source document or its indexed official copy."""

