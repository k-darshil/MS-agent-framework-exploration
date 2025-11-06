"""High-level orchestration for the learning project use case."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

from azure.ai.agents import AgentsClient, models
from azure.core.exceptions import HttpResponseError
from azure.core.credentials import TokenCredential
from rich.console import Console

from .config import AgentSettings
from .knowledge_base import RunbookStore
from .tooling import build_toolset


class AgentWorkflowError(RuntimeError):
    """Raised when the agent run cannot be completed successfully."""


@dataclass
class IncidentPlan:
    summary: str
    priority: str
    confidence: float
    affected_services: List[str]
    diagnostics: List[str]
    recommended_actions: List[str]
    communication_update: str

    @classmethod
    def from_payload(cls, payload: dict) -> "IncidentPlan":
        return cls(
            summary=payload.get("summary", ""),
            priority=payload.get("priority", "unknown"),
            confidence=float(payload.get("confidence", 0.5)),
            affected_services=list(payload.get("affected_services", [])),
            diagnostics=list(payload.get("diagnostics", [])),
            recommended_actions=list(payload.get("recommended_actions", [])),
            communication_update=payload.get("communication_update", ""),
        )


@dataclass
class WorkflowResult:
    agent_id: str
    thread_id: str
    run_id: str
    plan: IncidentPlan
    assistant_message: str
    message_history: List[str]


class IncidentTriageWorkflow:
    """Encapsulates the end-to-end flow for the incident triage demonstration."""

    def __init__(
        self,
        settings: AgentSettings,
        credential: TokenCredential,
        *,
        store: Optional[RunbookStore] = None,
        console: Optional[Console] = None,
    ) -> None:
        self.settings = settings
        self.console = console or Console(highlight=False)
        self.client = AgentsClient(endpoint=str(settings.endpoint), credential=credential)
        self.store = store or RunbookStore(settings.resolve_knowledge_base())
        self.toolset = build_toolset(settings, self.store)
        self._agent_id: Optional[str] = settings.agent_id
        self._instructions = settings.resolve_instructions()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ensure_agent(self) -> str:
        """Create a new agent if needed and return its identifier."""

        if self._agent_id:
            return self._agent_id

        try:
            agent = self.client.create_agent(
                model=self.settings.model_deployment,
                name="OpsPilot Planner",
                description="Operational triage orchestrator that leverages runbooks and metrics tools.",
                instructions=self._instructions,
                tools=self.toolset.definitions,
                tool_resources=self.toolset.resources,
                temperature=self.settings.default_temperature,
            )
        except HttpResponseError as exc:  # pragma: no cover - relies on live service
            raise AgentWorkflowError(f"Failed to create agent: {exc}") from exc

        self._agent_id = agent.id
        return agent.id

    def run(self, incident_prompt: str) -> WorkflowResult:
        """Execute the workflow for a single incident description."""

        agent_id = self.ensure_agent()
        thread_options = models.AgentThreadCreationOptions(
            messages=[
                models.ThreadMessageOptions(
                    role="user",
                    content=[models.MessageInputTextBlock(text=incident_prompt)],
                    metadata={"purpose": "incident-triage"},
                )
            ],
            tool_resources=self.toolset.resources,
        )

        response_format = self._json_response_format()

        try:
            run = self.client.create_thread_and_process_run(
                agent_id=agent_id,
                thread=thread_options,
                toolset=self.toolset,
                temperature=self.settings.default_temperature,
                max_completion_tokens=self.settings.max_completion_tokens,
                response_format=response_format,
            )
        except HttpResponseError as exc:  # pragma: no cover - relies on live service
            raise AgentWorkflowError(f"Agent run failed: {exc}") from exc

        if run.status != models.RunStatus.COMPLETED:
            raise AgentWorkflowError(f"Run ended in unexpected state: {run.status}")

        message_history = self._collect_message_history(run.thread_id)
        assistant_message = next((msg for msg in reversed(message_history) if msg.startswith("assistant:")), "")
        plan = self._extract_plan_from_history(message_history)

        return WorkflowResult(
            agent_id=agent_id,
            thread_id=run.thread_id,
            run_id=run.id,
            plan=plan,
            assistant_message=assistant_message,
            message_history=message_history,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _collect_message_history(self, thread_id: str) -> List[str]:
        history: List[str] = []
        messages = self.client.messages.list(thread_id=thread_id, order=models.ListSortOrder.ASC)
        for message in messages:
            role = message.role
            fragments = []
            if message.content:
                for content in message.content:
                    if isinstance(content, models.MessageTextContent) and content.text:
                        fragments.append(content.text.value)
            history.append(f"{role}: {'\n'.join(fragments).strip()}".strip())
        return history

    def _extract_plan_from_history(self, history: List[str]) -> IncidentPlan:
        for entry in reversed(history):
            if not entry.startswith("assistant:"):
                continue
            payload = entry.split(":", 1)[1].strip()
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict) and {"summary", "recommended_actions"} <= parsed.keys():
                    return IncidentPlan.from_payload(parsed)
            except json.JSONDecodeError:
                continue
        raise AgentWorkflowError("Assistant response did not contain a valid JSON payload.")

    def _json_response_format(self) -> models.ResponseFormatJsonSchemaType:
        schema = {
            "type": "object",
            "required": [
                "summary",
                "priority",
                "confidence",
                "affected_services",
                "diagnostics",
                "recommended_actions",
                "communication_update",
            ],
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Human readable overview of the incident." \
                    " Keep it under 120 words.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["P0", "P1", "P2", "P3"],
                    "description": "Suggested priority following on-call conventions.",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence score between 0 and 1 for the assessment.",
                },
                "affected_services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of services likely impacted by the incident.",
                },
                "diagnostics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key observations and diagnostic insights.",
                },
                "recommended_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered list of actions the on-call should execute next.",
                },
                "communication_update": {
                    "type": "string",
                    "description": "Suggested communication ready for stakeholders.",
                },
            },
        }
        return models.ResponseFormatJsonSchemaType(
            json_schema=models.ResponseFormatJsonSchema(
                name="incident_triage_report",
                description="Standard triage response format for OpsPilot.",
                schema=schema,
            )
        )


__all__ = [
    "IncidentPlan",
    "WorkflowResult",
    "IncidentTriageWorkflow",
    "AgentWorkflowError",
]
