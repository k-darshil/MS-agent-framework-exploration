# Microsoft Agent Framework Learning Guide

This guide walks through the incident-triage learning project implemented in this repository.
It explains how the Microsoft Azure AI Agent Framework pieces fit together, highlights
important code paths, and describes how to run and extend the sample.

## 1. Learning Objectives

- Understand the core primitives exposed by `azure-ai-agents` (`AgentsClient`, threads,
  runs, tools, and response formats).
- Learn how to expose local business logic to an agent by using `FunctionTool` and
  optional Azure AI Search resources.
- Observe a complete workflow that creates an agent, orchestrates a run, handles tool
  calls, and transforms the agent response into a structured JSON payload.
- Practice using the `uv` toolchain to manage Python 3.13 environments and package
  dependencies.

## 2. Architecture Overview

```
+-----------------------+           +------------------------------+
| Typer CLI (`cli.py`)  |  runs -->  | IncidentTriageWorkflow       |
|                       |           | (creates threads & runs)     |
+-----------+-----------+           +-----------+------------------+
            |                                   |
            | loads settings                    | builds ToolSet, loads KB
            v                                   v
+-----------+-----------+           +-----------+------------------+
| AgentSettings (`config.py`)      | FunctionTool (`tooling/…`)    |
| + credential hints               | + search_runbooks             |
| + knowledge base path            | + fetch_metric_snapshot       |
|                                  | + draft_communication_update  |
+----------------------------------+-------------------------------+
```

Key flows:

1. `ms_agent_learning.cli` loads `AgentSettings`, builds a credential chain, and invokes
   `IncidentTriageWorkflow.run()` with the user-provided incident description.
2. The workflow ensures an agent exists, creates a fresh thread, and executes
   `create_thread_and_process_run`. Tool definitions and tool resources come from the
   `ToolSet` assembled in `tooling/__init__.py`.
3. When the Azure model requests tool invocations, the framework executes the registered
   Python callables. Returned values are fed back into the run automatically.
4. The workflow fetches message history, extracts the final assistant JSON payload,
   and converts it into a strongly typed `IncidentPlan`.

## 3. Repository Layout

- `src/ms_agent_learning/config.py` – Loads environment-driven configuration, resolves
  embedded assets such as the system prompt, and documents credential expectations.
- `src/ms_agent_learning/knowledge_base.py` – Lightweight YAML-backed runbook store used
  by tools during triage.
- `src/ms_agent_learning/tooling/function_tools.py` – Builds the `FunctionTool` that exposes
  the local knowledge base and synthetic metrics to the agent. Docstrings decorate each
  function so the SDK can create JSON schemas automatically.
- `src/ms_agent_learning/workflow.py` – Implements the end-to-end agent workflow, including
  JSON schema enforcement on responses and run history retrieval.
- `src/ms_agent_learning/cli.py` – Typer-based CLI for configuration inspection and triage runs.
- `docs/` – Reference material, including this learning guide.

## 4. Prerequisites

1. Provision an Azure AI project with an Agents endpoint (public preview or later) and a
   deployed model that supports the Agents API.
2. Ensure you can authenticate using one of the supported Azure Identity mechanisms:
   - Service principal (recommended for automation)
   - Azure CLI cached credential
   - Interactive browser flow (development only)
3. Install `uv` (already handled in the setup script) and Python 3.13 via `uv` runtime
   management.
4. Optional: configure an Azure AI Search connection if you want to augment the agent with
   enterprise search. The project works without it by relying solely on function tools.

## 5. Environment Configuration

Create a `.env` file at the repository root (never commit secrets) with values similar to:

```
AZURE_AI_AGENT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
AZURE_AI_AGENT_MODEL=gpt-4o-mini
AZURE_CLIENT_ID=<guid>
AZURE_CLIENT_SECRET=<secret>
AZURE_TENANT_ID=<tenant>
AZURE_USE_CLI=false
AZURE_USE_INTERACTIVE=false
# Optional additions
# AZURE_AI_AGENT_ID=existing-agent-id
# KNOWLEDGE_BASE_PATH=/absolute/path/to/custom_runbooks.yaml
# AZURE_AI_SEARCH_CONNECTION_ID=/subscriptions/.../connections/<id>
# AZURE_AI_SEARCH_INDEX_NAME=runbooks-vector-index
```

The CLI offers `ms-agent-cli show-config` to confirm that settings are loaded correctly and to
see which credential mechanisms will be attempted.

## 6. Running the Sample

```bash
uv run ms-agent-cli show-config
uv run ms-agent-cli triage "PagerDuty P0: payments API timing out at Stripe"
```

The triage command prints a formatted summary, diagnostics, recommended actions, and the
suggested stakeholder communication. Use `--show-history` to inspect every exchanged
message (including raw JSON emitted by the assistant).

If you already created an agent via the Azure Portal or previous runs, set
`AZURE_AI_AGENT_ID` to reuse it. Otherwise, the workflow creates a new agent automatically
using the system prompt stored at `prompts/incident_system_prompt.md`.

## 7. Deep Dive: Tools and Runs

### Function Tool Generation

`build_ops_function_tool` constructs three functions:

1. `search_runbooks` uses the local YAML store to surface relevant remediation steps.
2. `fetch_metric_snapshot` calculates deterministic pseudo-metrics so the agent can reason
   about trends even without live observability APIs.
3. `draft_communication_update` formats a stakeholder update, ensuring the agent links
   technical insight with communication guidance.

Because the framework reads type hints and docstrings to craft JSON schemas, each function
includes explicit `:param` descriptions and returns JSON or Markdown strings for clarity.

### Workflow Execution

`IncidentTriageWorkflow` demonstrates these API calls:

- `AgentsClient.create_agent` – Provisioning with tool definitions and resources.
- `AgentsClient.create_thread_and_process_run` – Single-call helper that creates the thread,
  starts a run, and automatically services tool calls until completion.
- `client.messages.list` – Fetching conversation history to display in the CLI and parse the
  final assistant response.

The workflow enforces a JSON schema via `ResponseFormatJsonSchemaType`. This ensures the
assistant replies with machine-readable data that maps neatly to the `IncidentPlan` dataclass.

## 8. Extending the Project

- **Add real telemetry**: replace `fetch_metric_snapshot` with calls to Azure Monitor or your
  observability stack. Return structured JSON that the agent can parse.
- **Vectorised knowledge**: integrate Azure AI Search or vector stores by populating the
  optional configuration fields and attaching files through `client.vector_stores`.
- **Multi-agent orchestration**: spawn specialised agents (e.g. planner, communicator) and
  pipeline their outputs. The same workflow class can orchestrate multiple runs sequentially.
- **Streaming UX**: switch to the SDK's streaming APIs to emit partial results in real time
  (see `AgentRunStream` in `azure.ai.agents.models`).

## 9. Troubleshooting

- Authentication failures usually mean the credential chain cannot obtain a token. Run
  `az login` for CLI credentials or double-check client secret values.
- `Run ended in unexpected state` indicates the model halted before completing. Inspect
  run steps via the Azure portal or enable `--show-history` for more context.
- Ensure your model deployment supports the Agents API (e.g. GPT-4o, GPT-4o-mini). Not all
  models expose tool-calling features.

## 10. Related Resources

- [Azure AI Agent Service documentation](https://learn.microsoft.com/azure/ai-services/agents)
- [Azure AI Agents SDK reference (Python)](https://learn.microsoft.com/python/api/azure-ai-agents)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Typer CLI framework](https://typer.tiangolo.com/)

---
Happy exploring! Use issues or notes within this repo to capture insights as you experiment
with additional capabilities of the Microsoft Agent Framework.
