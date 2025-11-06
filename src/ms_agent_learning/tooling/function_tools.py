"""Function tool definitions that integrate the local knowledge base."""
from __future__ import annotations

import json
import statistics
from hashlib import sha256
from typing import Iterable, Set

from azure.ai.agents import models

from ..knowledge_base import RunbookEntry, RunbookStore


def _format_runbook(entry: RunbookEntry) -> dict:
    return {
        "id": entry.id,
        "service": entry.service,
        "issue": entry.issue,
        "summary": entry.summary,
        "diagnostics": entry.diagnostics,
        "remediation": entry.remediation,
        "communications": entry.communications,
    }


def build_ops_function_tool(store: RunbookStore) -> models.FunctionTool:
    """Create a FunctionTool exposing domain-specific helpers."""

    def search_runbooks(service: str, issue: str | None = None, top_k: int = 3) -> str:
        """Return the most relevant runbook entries for the provided service and issue.

        :param service: The high level capability or subsystem to filter by.
        :param issue: Optional free-text description of the observed symptom.
        :param top_k: Maximum number of runbooks to include.
        :returns: A JSON string describing the matching runbooks.
        """

        matches = store.search(service, issue, top_k=top_k)
        payload = {"service": service, "issue": issue, "matches": [_format_runbook(entry) for entry in matches]}
        return json.dumps(payload, indent=2)

    def fetch_metric_snapshot(metric_name: str, service: str, lookback_minutes: int = 60) -> str:
        """Return a deterministic pseudo metric summary for the requested service.

        :param metric_name: Name of the metric (e.g. error_rate, latency_ms).
        :param service: Service name to scope the metric.
        :param lookback_minutes: Time window to aggregate over.
        :returns: A JSON string containing aggregated statistics for quick triage.
        """

        seed = sha256(f"{service}:{metric_name}:{lookback_minutes}".encode("utf-8")).digest()
        sample = [(seed[i] % 100) / 10 for i in range(12)]
        payload = {
            "metric": metric_name,
            "service": service,
            "lookback_minutes": lookback_minutes,
            "avg": round(statistics.fmean(sample), 2),
            "p95": round(sorted(sample)[-2], 2),
            "samples": sample,
        }
        return json.dumps(payload, indent=2)

    def draft_communication_update(audience: str, summary: str, actions: Iterable[str] | None = None) -> str:
        """Draft a status update tailored for the requested audience.

        :param audience: Target audience (e.g. customers, executives, sre-team).
        :param summary: Short narrative of the incident status.
        :param actions: Optional list of next steps that will appear as bullet points.
        :returns: Markdown-formatted communication block.
        """

        actions_list = list(actions or [])
        header = f"Update for {audience.strip().title()}"
        lines = [header, "", summary.strip()]
        if actions_list:
            lines.append("")
            lines.append("Next actions:")
            for idx, item in enumerate(actions_list, start=1):
                lines.append(f"{idx}. {item}")
        return "\n".join(lines)

    function_set: Set = {search_runbooks, fetch_metric_snapshot, draft_communication_update}
    return models.FunctionTool(function_set)


__all__ = ["build_ops_function_tool"]
