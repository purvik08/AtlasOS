"""Authentication and authorization for Atlas OS REST API."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from typing import Any

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, Field

from atlas.config.settings import AtlasConfig
from atlas.secrets import get_secrets_manager


class APIKey(BaseModel):
    """API Key record."""
    key_hash: str
    name: str
    created_at: float = Field(default_factory=time.time)
    last_used: float | None = None
    expires_at: float | None = None
    scopes: list[str] = Field(default_factory=list)
    is_active: bool = True


class AuthManager:
    """Manages API key authentication.
    
    Keys are stored in the secure secrets manager (keyring/encrypted file).
    This class validates keys by reading from the secrets manager on each check,
    ensuring consistency across processes.
    """

    # Prefix for API key secrets
    _KEY_PREFIX = "atlas_api_key_"
    
    # Atlas API key prefix
    _ATLAS_KEY_PREFIX = "atlas_"

    def __init__(self, config: AtlasConfig) -> None:
        self.config = config
        self._secrets_mgr = get_secrets_manager()
        self._secrets_mgr.initialize()

    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_stored_key(self, key_hash: str) -> APIKey | None:
        """Retrieve a stored API key record from secrets."""
        secret_key = f"{self._KEY_PREFIX}{key_hash}"
        stored = self._secrets_mgr.get_secret(secret_key)
        if not stored:
            return None
        
        try:
            data = json.loads(stored)
            return APIKey(**data)
        except Exception:
            return None

    def _store_key(self, api_key: APIKey) -> None:
        """Store an API key record in secrets."""
        secret_key = f"{self._KEY_PREFIX}{api_key.key_hash}"
        self._secrets_mgr.set_secret(secret_key, json.dumps(api_key.model_dump()))

    def create_api_key(self, name: str, scopes: list[str] | None = None) -> tuple[str, APIKey]:
        """Create a new API key."""
        if scopes is None:
            scopes = ["chat", "models", "sessions"]

        # Generate secure key
        raw_key = f"{self._ATLAS_KEY_PREFIX}{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        
        api_key = APIKey(
            key_hash=key_hash,
            name=name,
            scopes=scopes,
        )
        
        self._store_key(api_key)
        return raw_key, api_key

    def validate_api_key(self, key: str) -> APIKey | None:
        """Validate an API key and return the record if valid."""
        if not key:
            return None
            
        # Only validate keys with our prefix
        if not key.startswith(self._ATLAS_KEY_PREFIX):
            return None
            
        key_hash = self._hash_key(key)
        api_key = self._get_stored_key(key_hash)
        
        if not api_key or not api_key.is_active:
            return None
        
        if api_key.expires_at and time.time() > api_key.expires_at:
            return None
        
        # Update last used
        api_key.last_used = time.time()
        self._store_key(api_key)
        return api_key

    def revoke_api_key(self, key: str) -> bool:
        """Revoke an API key."""
        if not key.startswith(self._ATLAS_KEY_PREFIX):
            return False
            
        key_hash = self._hash_key(key)
        secret_key = f"{self._KEY_PREFIX}{key_hash}"
        
        # Check if key exists
        api_key = self._get_stored_key(key_hash)
        if not api_key:
            return False
            
        api_key.is_active = False
        self._store_key(api_key)
        return True

    def list_keys(self) -> list[dict[str, Any]]:
        """List all API keys (without raw values)."""
        keys = []
        all_secrets = self._secrets_mgr.list_secrets()
        
        for secret_key in all_secrets:
            if secret_key.startswith(self._KEY_PREFIX):
                stored = self._secrets_mgr.get_secret(secret_key)
                if stored:
                    try:
                        data = json.loads(stored)
                        api_key = APIKey(**data)
                        keys.append({
                            "name": api_key.name,
                            "key_prefix": f"{self._ATLAS_KEY_PREFIX}{api_key.key_hash[:8]}...",
                            "scopes": api_key.scopes,
                            "created_at": api_key.created_at,
                            "last_used": api_key.last_used,
                            "expires_at": api_key.expires_at,
                            "is_active": api_key.is_active,
                        })
                    except Exception:
                        pass
        return keys


# Global instance
_auth_manager: AuthManager | None = None


def get_auth_manager(config: AtlasConfig | None = None) -> AuthManager | None:
    """Get or create the global auth manager."""
    global _auth_manager
    if _auth_manager is None and config:
        _auth_manager = AuthManager(config)
    return _auth_manager


async def require_auth(
    request: Request,
    authorization: str | None = Header(None),
) -> APIKey | None:
    """FastAPI dependency for API key authentication.
    
    If no Authorization header is provided, local/offline access is permitted.
    If an Authorization header is provided, it is validated against API keys or JWT tokens.
    """
    if authorization is None:
        return None

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = parts[1].strip()
    auth_mgr = getattr(request.app.state, "auth_manager", None) or _auth_manager
    if auth_mgr is not None:
        api_key = auth_mgr.validate_api_key(token)
        if api_key is not None:
            return api_key

    local_auth = getattr(request.app.state, "local_auth_manager", None)
    if local_auth is not None:
        user = local_auth.validate_token(token)
        if user is not None:
            user_role = getattr(user, "role", None)
            role_value = user_role.value if hasattr(user_role, "value") else str(user_role or "user")
            return APIKey(
                key_hash=user.username,
                name=user.username,
                scopes=[role_value] if role_value else ["user"],
                is_active=getattr(user, "is_active", True),
            )

    raise HTTPException(status_code=401, detail="Invalid or expired API key")


def set_auth_manager(auth_manager: AuthManager) -> None:
    """Set the global auth manager for the require_auth dependency."""
    global _auth_manager
    _auth_manager = auth_manager