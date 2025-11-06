from pathlib import Path

from ms_agent_learning.knowledge_base import RunbookStore
from ms_agent_learning.tooling.function_tools import build_ops_function_tool


def test_function_tool_definitions_include_runbook_search(tmp_path: Path) -> None:
    data_file = tmp_path / "kb.yaml"
    data_file.write_text(
        """
- id: example
  service: svc
  issue: outage
  summary: desc
  diagnostics: []
  remediation: []
  communications: []
"""
    )
    store = RunbookStore(data_file)
    tool = build_ops_function_tool(store)

    # ensure schema generation picks up docstrings
    definition_names = {definition.function.name for definition in tool.definitions}
    assert {"search_runbooks", "fetch_metric_snapshot", "draft_communication_update"} <= definition_names
