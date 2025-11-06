"""Tool helpers for the learning project."""
from __future__ import annotations

from azure.ai.agents import models

from ..config import AgentSettings
from ..knowledge_base import RunbookStore
from .function_tools import build_ops_function_tool


def build_toolset(settings: AgentSettings, store: RunbookStore) -> models.ToolSet:
    """Compose the ToolSet that will be provided to the agent."""

    toolset = models.ToolSet()
    toolset.add(build_ops_function_tool(store))

    if settings.azure_search_connection_id and settings.azure_search_index_name:
        toolset.add(
            models.AzureAISearchTool(
                index_connection_id=settings.azure_search_connection_id,
                index_name=settings.azure_search_index_name,
                top_k=settings.azure_search_top_k,
            )
        )

    return toolset


__all__ = ["build_toolset"]
