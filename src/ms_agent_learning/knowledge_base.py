"""Simple in-memory knowledge base for runbook style content."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import yaml


@dataclass(frozen=True)
class RunbookEntry:
    """Domain object representing a single runbook document."""

    id: str
    service: str
    issue: str
    summary: str
    diagnostics: List[str]
    remediation: List[str]
    communications: List[str]

    @staticmethod
    def from_dict(payload: dict) -> "RunbookEntry":
        return RunbookEntry(
            id=payload["id"],
            service=payload["service"],
            issue=payload["issue"],
            summary=payload["summary"],
            diagnostics=list(payload.get("diagnostics", [])),
            remediation=list(payload.get("remediation", [])),
            communications=list(payload.get("communications", [])),
        )


class RunbookStore:
    """Loads runbooks from YAML and supports lightweight semantic filtering."""

    def __init__(self, source: Path):
        self.source = source
        self._entries = self._load()

    def _load(self) -> List[RunbookEntry]:
        data = yaml.safe_load(self.source.read_text(encoding="utf-8"))
        if not isinstance(data, list):  # pragma: no cover - input validation guardrail
            raise ValueError("Runbook YAML must contain a list of entries")
        return [RunbookEntry.from_dict(item) for item in data]

    @property
    def entries(self) -> Iterable[RunbookEntry]:
        return tuple(self._entries)

    def search(self, service: str, issue: str | None = None, top_k: int = 3) -> List[RunbookEntry]:
        """Naive scoring by matching service and issue keywords."""

        service_key = service.lower()
        issue_key = (issue or "").lower()

        scored: List[tuple[int, RunbookEntry]] = []
        for entry in self._entries:
            score = 0
            if service_key and service_key in entry.service.lower():
                score += 2
            if issue_key and issue_key in entry.issue.lower():
                score += 1
            if issue_key and issue_key in entry.summary.lower():
                score += 1

            if score:
                scored.append((score, entry))

        if not scored:
            return []

        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]


__all__ = ["RunbookEntry", "RunbookStore"]
