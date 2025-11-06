# MS Agent Framework Exploration

This repository contains a hands-on learning project for the Microsoft Azure AI Agent
Framework. It showcases a realistic incident-triage assistant that orchestrates agents,
function tools, and structured responses using Python 3.13 with the `uv` toolchain.

## Quick Start

1. Install dependencies and create the virtual environment (already set up when you ran the
   bootstrap script):
   ```bash
   uv venv --python 3.13
   uv sync
   ```
2. Configure credentials and agent settings in a `.env` file (see the [learning guide](docs/LEARNING_GUIDE.md#5-environment-configuration)).
3. Explore the CLI:
   ```bash
   uv run ms-agent-cli show-config
   uv run ms-agent-cli triage "Example incident summary"
   ```

## Documentation

The accompanying [learning guide](docs/LEARNING_GUIDE.md) explains the architecture,
configuration, and extension points in depth. Start there to understand how the project
is structured and how each component maps to Azure AI Agent Framework concepts.

## Tests

Unit tests cover the knowledge base loader and tool metadata.
Run them with:

```bash
uv run pytest
```

## Project Structure

- `src/ms_agent_learning/` – Python package implementing settings, tooling, workflow, and CLI.
- `docs/LEARNING_GUIDE.md` – Tutorial-style documentation for the project.
- `tests/` – Lightweight unit tests.

Feel free to fork and iterate. Pull requests welcome if you discover improvements while
experimenting with additional Microsoft Agent Framework capabilities.
