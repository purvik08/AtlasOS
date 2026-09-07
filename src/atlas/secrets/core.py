"""Secure secrets management for Atlas OS.

Provides encrypted storage for API keys and other sensitive configuration.
Uses platform-specific keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
with a fallback to encrypted file storage.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Service name for keyring
KEYRING_SERVICE = "atlas-os"
# Fallback storage location
SECRETS_DIR = Path.home() / ".atlas" / "secrets"
SECRETS_FILE = SECRETS_DIR / "vault.enc"
KEYS_INDEX_FILE = SECRETS_DIR / "keys.json"  # Unencrypted index of stored keys
SALT_FILE = SECRETS_DIR / "salt"


class SecretsManager:
    """Manages encrypted secrets storage with keyring backend and file fallback."""

    def __init__(self, master_password: str | None = None) -> None:
        self._master_password = master_password or os.environ.get("ATLAS_MASTER_PASSWORD")
        self._fernet: Fernet | None = None
        self._keyring_available = self._check_keyring()
        self._initialized = False

    def _check_keyring(self) -> bool:
        """Check if system keyring is available."""
        try:
            import keyring
            keyring.get_keyring()
            return True
        except Exception:
            return False

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one."""
        if SALT_FILE.exists():
            return SALT_FILE.read_bytes()
        salt = os.urandom(16)
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        SALT_FILE.write_bytes(salt)
        return salt

    def _init_fernet(self) -> None:
        """Initialize Fernet cipher for file-based encryption."""
        if self._fernet is not None:
            return
        if not self._master_password:
            raise ValueError("Master password required for file-based encryption")
        salt = self._get_or_create_salt()
        key = self._derive_key(self._master_password, salt)
        self._fernet = Fernet(key)

    def initialize(self, master_password: str | None = None) -> bool:
        """Initialize the secrets manager."""
        if master_password:
            self._master_password = master_password
        elif not self._master_password and not self._keyring_available:
            # Generate a random master password for first-time setup
            self._master_password = base64.urlsafe_b64encode(os.urandom(32)).decode()
            logger.info("Generated master password (save this): %s", self._master_password)
        
        if self._master_password and not self._keyring_available:
            self._init_fernet()
        
        self._initialized = True
        return True

    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret value."""
        if not self._initialized:
            self.initialize()
        
        # Try keyring first
        if self._keyring_available:
            try:
                import keyring
                keyring.set_password(KEYRING_SERVICE, key, value)
                # Also track in file for listing
                self._track_key_in_file(key)
                return True
            except Exception as exc:
                logger.warning("Keyring write failed, falling back to file: %s", exc)
        
        # Fallback to encrypted file
        return self._write_file_secrets({key: value})

    def _track_key_in_file(self, key: str) -> None:
        """Track a key in file storage without storing the value."""
        try:
            # Read existing keys index
            if KEYS_INDEX_FILE.exists():
                keys = json.loads(KEYS_INDEX_FILE.read_text())
            else:
                keys = []
            
            if key not in keys:
                keys.append(key)
                SECRETS_DIR.mkdir(parents=True, exist_ok=True)
                KEYS_INDEX_FILE.write_text(json.dumps(keys))
        except Exception:
            pass  # Ignore tracking errors

    def get_secret(self, key: str) -> str | None:
        """Retrieve a secret value."""
        if not self._initialized:
            self.initialize()
        
        # Try keyring first
        if self._keyring_available:
            try:
                import keyring
                value = keyring.get_password(KEYRING_SERVICE, key)
                if value:
                    return value
            except Exception:
                pass
        
        # Fallback to encrypted file
        secrets = self._read_file_secrets()
        return secrets.get(key)

    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        if not self._initialized:
            self.initialize()
        
        success = False
        if self._keyring_available:
            try:
                import keyring
                keyring.delete_password(KEYRING_SERVICE, key)
                success = True
            except Exception:
                pass
        
        # Also remove from file storage
        secrets = self._read_file_secrets()
        if key in secrets:
            del secrets[key]
            self._write_file_secrets(secrets)
            success = True
        
        # Also remove from keys index
        if KEYS_INDEX_FILE.exists():
            try:
                keys = json.loads(KEYS_INDEX_FILE.read_text())
                if key in keys:
                    keys.remove(key)
                    KEYS_INDEX_FILE.write_text(json.dumps(keys))
                    success = True
            except Exception:
                pass
        
        return success

    def list_secrets(self) -> list[str]:
        """List all secret keys (not values)."""
        if not self._initialized:
            self.initialize()
        
        keys = set()
        
        # Read from keys index file
        if KEYS_INDEX_FILE.exists():
            try:
                keys.update(json.loads(KEYS_INDEX_FILE.read_text()))
            except Exception:
                pass
        
        # Also check encrypted file for any legacy entries
        secrets = self._read_file_secrets()
        keys.update(secrets.keys())
        
        return sorted(keys)

    def _read_file_secrets(self) -> dict[str, str]:
        """Read and decrypt secrets from file."""
        if not SECRETS_FILE.exists():
            return {}
        if not self._fernet:
            self._init_fernet()
        
        if self._fernet is None:
            return {}
        
        try:
            encrypted = SECRETS_FILE.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as exc:
            logger.warning("Failed to read secrets file: %s", exc)
            return {}

    def _write_file_secrets(self, secrets: dict[str, str]) -> bool:
        """Encrypt and write secrets to file."""
        if not self._fernet:
            self._init_fernet()
        
        if self._fernet is None:
            return False
        
        try:
            data = json.dumps(secrets).encode()
            encrypted = self._fernet.encrypt(data)
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            SECRETS_FILE.write_bytes(encrypted)
            return True
        except Exception as exc:
            logger.error("Failed to write secrets file: %s", exc)
            return False

    def migrate_to_keyring(self) -> int:
        """Migrate file-based secrets to system keyring."""
        if not self._keyring_available:
            return 0
        
        secrets = self._read_file_secrets()
        count = 0
        for key, value in secrets.items():
            try:
                import keyring
                keyring.set_password(KEYRING_SERVICE, key, value)
                count += 1
            except Exception:
                pass
        return count


# Global instance
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global secrets manager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def set_api_key(provider: str, api_key: str) -> bool:
    """Store an API key for a provider."""
    manager = get_secrets_manager()
    return manager.set_secret(f"api_key.{provider}", api_key)


def get_api_key(provider: str) -> str | None:
    """Retrieve an API key for a provider."""
    manager = get_secrets_manager()
    return manager.get_secret(f"api_key.{provider}")


def delete_api_key(provider: str) -> bool:
    """Delete an API key for a provider."""
    manager = get_secrets_manager()
    return manager.delete_secret(f"api_key.{provider}")


def list_api_keys() -> list[str]:
    """List all stored API key providers."""
    manager = get_secrets_manager()
    all_keys = manager.list_secrets()
    return [k.replace("api_key.", "") for k in all_keys if k.startswith("api_key.")]


# Configuration keys that can be stored as secrets
SECRET_CONFIG_KEYS = {
    "gemini_api_key": "gemini",
    "deepseek_api_key": "deepseek",
    "kimi_api_key": "kimi",
    "qwen_api_key": "qwen",
}


def sync_secrets_to_config(config: Any) -> None:
    """Sync stored secrets to config object."""
    ai_config = getattr(config, "ai", None)
    if not ai_config:
        return
    
    for config_key, provider in SECRET_CONFIG_KEYS.items():
        stored_key = get_api_key(provider)
        if stored_key and not getattr(ai_config, config_key, ""):
            setattr(ai_config, config_key, stored_key)
            logger.debug("Loaded %s from secure storage", config_key)


def sync_config_to_secrets(config: Any) -> None:
    """Sync config API keys to secure storage."""
    ai_config = getattr(config, "ai", None)
    if not ai_config:
        return
    
    for config_key, provider in SECRET_CONFIG_KEYS.items():
        value = getattr(ai_config, config_key, "")
        if value and not get_api_key(provider):
            set_api_key(provider, value)
            logger.debug("Stored %s in secure storage", config_key)