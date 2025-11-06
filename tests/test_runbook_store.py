from pathlib import Path

from ms_agent_learning.knowledge_base import RunbookStore


def test_search_returns_expected_order(tmp_path: Path) -> None:
    content = """
- id: s1
  service: foo
  issue: latency
  summary: foo latency issue
  diagnostics: [diag]
  remediation: [fix]
  communications: []
- id: s2
  service: foo-bar
  issue: auth failure
  summary: auth summary
  diagnostics: []
  remediation: []
  communications: []
"""
    data_file = tmp_path / "kb.yaml"
    data_file.write_text(content)

    store = RunbookStore(data_file)
    results = store.search("foo", "latency")
    assert results
    assert results[0].id == "s1"


def test_search_handles_no_matches(tmp_path: Path) -> None:
    content = """[]"""
    data_file = tmp_path / "kb.yaml"
    data_file.write_text(content)

    store = RunbookStore(data_file)
    assert store.search("missing") == []
