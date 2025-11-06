"""Credential helpers for Azure AI Agents."""
from __future__ import annotations

from typing import List

from azure.core.credentials import TokenCredential
from azure.identity import (
    AzureCliCredential,
    ChainedTokenCredential,
    ClientSecretCredential,
    DefaultAzureCredential,
    InteractiveBrowserCredential,
)

from .config import AgentSettings, CredentialHints


def build_credential(settings: AgentSettings) -> TokenCredential:
    """Build a TokenCredential chain based on the configured options."""

    candidates: List[TokenCredential] = []

    if settings.has_service_principal:
        candidates.append(
            ClientSecretCredential(
                tenant_id=settings.tenant_id,  # type: ignore[arg-type]
                client_id=settings.client_id,  # type: ignore[arg-type]
                client_secret=settings.client_secret,  # type: ignore[arg-type]
            )
        )

    if settings.use_cli_credential:
        candidates.append(AzureCliCredential())

    if settings.use_interactive_browser:
        candidates.append(InteractiveBrowserCredential())

    # DefaultAzureCredential already covers multiple fallbacks, but we keep it last so explicit
    # credentials take precedence and so we benefit from managed identity if available.
    candidates.append(
        DefaultAzureCredential(
            exclude_cli_credential=not settings.use_cli_credential,
            exclude_interactive_browser_credential=not settings.use_interactive_browser,
        )
    )

    if len(candidates) == 1:
        return candidates[0]

    return ChainedTokenCredential(*candidates)


def describe_credential_plan(settings: AgentSettings) -> CredentialHints:
    """Small helper that summarises which credential types will be tried."""

    return CredentialHints(
        use_service_principal=settings.has_service_principal,
        include_cli=settings.use_cli_credential,
        include_interactive=settings.use_interactive_browser,
    )
