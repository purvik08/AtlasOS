"""Atlas OS Secrets Management.

Provides secure storage for API keys and sensitive configuration.
"""

from __future__ import annotations

from atlas.secrets.core import (
    SecretsManager,
    delete_api_key,
    get_api_key,
    get_secrets_manager,
    list_api_keys,
    set_api_key,
    sync_config_to_secrets,
    sync_secrets_to_config,
)

__all__ = [
    "SecretsManager",
    "get_secrets_manager",
    "set_api_key",
    "get_api_key",
    "delete_api_key",
    "list_api_keys",
    "sync_secrets_to_config",
    "sync_config_to_secrets",
]