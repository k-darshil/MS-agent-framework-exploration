"""Command line interface for the learning project."""
from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .auth import build_credential, describe_credential_plan
from .config import AgentSettings, load_settings
from .workflow import AgentWorkflowError, IncidentTriageWorkflow

app = typer.Typer(help="Utilities for exploring the Microsoft Agent Framework use case.")


@app.command()
def show_config() -> None:
    """Print the active configuration after loading environment variables."""

    console = Console()
    settings = load_settings()
    hints = describe_credential_plan(settings)

    table = Table(title="Agent Configuration", show_lines=True)
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Endpoint", str(settings.endpoint))
    table.add_row("Model Deployment", settings.model_deployment)
    table.add_row("Agent ID (reuse)", settings.agent_id or "<auto>")
    table.add_row("Knowledge Base", str(settings.resolve_knowledge_base()))
    table.add_row("Azure Search Connection", settings.azure_search_connection_id or "<disabled>")
    table.add_row("Azure Search Index", settings.azure_search_index_name or "<n/a>")
    table.add_row("Temperature", f"{settings.default_temperature}")
    table.add_row("Max Completion Tokens", str(settings.max_completion_tokens))
    table.add_row(
        "Credential Plan",
        json.dumps(
            {
                "service_principal": hints.use_service_principal,
                "cli": hints.include_cli,
                "interactive": hints.include_interactive,
            },
            indent=2,
        ),
    )

    console.print(table)


@app.command()
def triage(
    description: str = typer.Argument(..., help="Incident summary or on-call page content."),
    show_history: bool = typer.Option(False, help="Display the full message history after the run."),
) -> None:
    """Run the incident triage workflow against the configured Azure AI Agent project."""

    console = Console()
    settings = load_settings()
    credential = build_credential(settings)
    workflow = IncidentTriageWorkflow(settings, credential, console=console)

    console.print(f"[bold green]Running triage with deployment:[/] {settings.model_deployment}")

    try:
        result = workflow.run(description)
    except AgentWorkflowError as exc:
        console.print(f"[bold red]Agent workflow failed:[/] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[bold blue]Incident Summary[/]")
    console.print(result.plan.summary)
    console.print()

    console.print("[bold blue]Recommended Priority:[/]", result.plan.priority)
    console.print("[bold blue]Confidence:[/]", f"{result.plan.confidence:.2f}")
    console.print("[bold blue]Affected Services:[/]", ", ".join(result.plan.affected_services) or "<unknown>")

    console.print()
    console.print("[bold blue]Diagnostics[/]")
    for item in result.plan.diagnostics:
        console.print(f" • {item}")

    console.print()
    console.print("[bold blue]Recommended Actions[/]")
    for idx, action in enumerate(result.plan.recommended_actions, start=1):
        console.print(f" {idx}. {action}")

    console.print()
    console.print("[bold blue]Communication Update[/]")
    console.print(result.plan.communication_update or "<none>")

    console.print()
    console.print(
        "[dim]Trace info[/]",
        {
            "agent_id": result.agent_id,
            "thread_id": result.thread_id,
            "run_id": result.run_id,
        },
    )

    if show_history:
        console.print()
        console.print("[bold blue]Message History[/]")
        for message in result.message_history:
            console.print(f"- {message}")


def app_entrypoint() -> None:  # pragma: no cover - thin wrapper
    """Allow ``python -m ms_agent_learning.cli`` execution."""

    app()


if __name__ == "__main__":  # pragma: no cover - CLI entry
    app_entrypoint()
