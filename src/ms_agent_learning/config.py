"""Configuration helpers for the MS Agent learning project."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Optional

from pydantic import Field, HttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Central configuration for connecting to Azure AI Agents and managing defaults.

    Environment variables (or values in a local ``.env``) that this class understands::

        AZURE_AI_AGENT_ENDPOINT=...  # Full endpoint including project path
        AZURE_AI_AGENT_MODEL=...     # Deployment name in the Azure AI project
        AZURE_AI_AGENT_ID=...        # Optional, reuse an existing agent id
        AZURE_TENANT_ID=...          # For service principal authentication
        AZURE_CLIENT_ID=...
        AZURE_CLIENT_SECRET=...
        AZURE_USE_CLI=true           # Optionally add AzureCLI credential into the chain
        AZURE_USE_INTERACTIVE=false  # Allow fall back to interactive browser login
        KNOWLEDGE_BASE_PATH=data/runbooks.yaml
        AZURE_AI_SEARCH_CONNECTION_ID=connection:...  # Optional Azure AI Search tool config
        AZURE_AI_SEARCH_INDEX_NAME=myindex
        AZURE_AI_SEARCH_TOP_K=5
        AGENT_TEMPERATURE=0.2
        AGENT_MAX_COMPLETION_TOKENS=2048
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    endpoint: HttpUrl = Field(..., alias="AZURE_AI_AGENT_ENDPOINT")
    model_deployment: str = Field(..., alias="AZURE_AI_AGENT_MODEL")
    agent_id: Optional[str] = Field(None, alias="AZURE_AI_AGENT_ID")

    tenant_id: Optional[str] = Field(None, alias="AZURE_TENANT_ID")
    client_id: Optional[str] = Field(None, alias="AZURE_CLIENT_ID")
    client_secret: Optional[str] = Field(None, alias="AZURE_CLIENT_SECRET")

    use_cli_credential: bool = Field(default=False, alias="AZURE_USE_CLI")
    use_interactive_browser: bool = Field(default=False, alias="AZURE_USE_INTERACTIVE")

    knowledge_base_path: Optional[Path] = Field(None, alias="KNOWLEDGE_BASE_PATH")

    azure_search_connection_id: Optional[str] = Field(None, alias="AZURE_AI_SEARCH_CONNECTION_ID")
    azure_search_index_name: Optional[str] = Field(None, alias="AZURE_AI_SEARCH_INDEX_NAME")
    azure_search_top_k: int = Field(default=5, alias="AZURE_AI_SEARCH_TOP_K", ge=1, le=15)

    default_temperature: float = Field(default=0.25, alias="AGENT_TEMPERATURE", ge=0.0, le=2.0)
    max_completion_tokens: int = Field(default=2048, alias="AGENT_MAX_COMPLETION_TOKENS", ge=256, le=4096)

    instructions_path: Optional[Path] = Field(None, alias="AGENT_INSTRUCTIONS_PATH")

    @computed_field
    @property
    def has_service_principal(self) -> bool:
        """Whether full client credential information is configured."""

        return bool(self.tenant_id and self.client_id and self.client_secret)

    def resolve_knowledge_base(self) -> Path:
        """Resolve the path for the default knowledge base data file."""

        if self.knowledge_base_path:
            return Path(self.knowledge_base_path).expanduser().resolve()

        with resources.as_file(resources.files("ms_agent_learning.data").joinpath("runbooks.yaml")) as file_path:
            return file_path

    def resolve_instructions(self) -> str:
        """Load the system prompt used by the orchestrator agent."""

        instructions_file = self.instructions_path
        if instructions_file is None:
            instructions_file = resources.files("ms_agent_learning.prompts").joinpath("incident_system_prompt.md")

        with resources.as_file(instructions_file) as path:
            return path.read_text(encoding="utf-8")


@dataclass
class CredentialHints:
    """Explain which credential sources will be attempted."""

    use_service_principal: bool
    include_cli: bool
    include_interactive: bool


@lru_cache(maxsize=1)
def load_settings() -> AgentSettings:
    """Cached helper so modules can share the same settings instance."""

    return AgentSettings()
