"""Local authentication manager for Atlas OS.

Provides:
- bcrypt password hashing (via passlib or PBKDF2 fallback)
- JWT issuance and validation (via PyJWT or built-in HMAC-SHA256)
- User persistence in data/users.json (protected by secrets manager)

Passwords are NEVER stored in plaintext.
JWT secret is generated once and stored in the secrets manager.

Design: OAuth/OIDC can be added in v1.4.0 by implementing an alternate
auth manager that still produces User objects — the middleware and
authorization logic in middleware.py remain unchanged.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from atlas.auth.models import (
    JWTClaims,
    LoginRequest,
    Role,
    TokenResponse,
    User,
    UserRecord,
)

logger = logging.getLogger(__name__)

# Token expiry defaults
_ACCESS_TOKEN_EXPIRE_SECONDS = 3600      # 1 hour
_REFRESH_TOKEN_EXPIRE_SECONDS = 86400 * 7  # 7 days

# Revoked token JTIs (in-process set; cleared on restart)
# In v1.4.0 this could move to Redis or a persistent store.
_revoked_jtis: set[str] = set()

# Optional: PyJWT
try:
    import jwt as _pyjwt
    _JWT_AVAILABLE = True
except ImportError:
    _pyjwt = None  # type: ignore[assignment]
    _JWT_AVAILABLE = False

# Optional: passlib bcrypt
try:
    from passlib.context import CryptContext  # type: ignore[import]
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False
    _pwd_context = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Password hashing helpers
# ---------------------------------------------------------------------------

def _hash_password(plain: str) -> str:
    """Hash a plain-text password. Uses bcrypt if available, PBKDF2 otherwise."""
    if _BCRYPT_AVAILABLE and _pwd_context is not None:
        return _pwd_context.hash(plain)
    # Fallback: PBKDF2-HMAC-SHA256 (standard library, zero external deps)
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260_000)
    return f"pbkdf2${salt}${dk.hex()}"


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a hash."""
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        if _BCRYPT_AVAILABLE and _pwd_context is not None:
            return _pwd_context.verify(plain, hashed)
        return False
    if hashed.startswith("pbkdf2$"):
        parts = hashed.split("$", 2)
        if len(parts) == 3:
            _, salt, dk_hex = parts
            dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260_000)
            return secrets.compare_digest(dk.hex(), dk_hex)
    return False


# ---------------------------------------------------------------------------
# JWT HS256 helpers (works with or without PyJWT)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data_str: str) -> bytes:
    padding = (4 - len(data_str) % 4) % 4
    return base64.urlsafe_b64decode((data_str + "=" * padding).encode("ascii"))


def _encode_jwt(payload: dict[str, Any], secret: str) -> str:
    """Encode JWT claims using HS256."""
    if _JWT_AVAILABLE and _pyjwt is not None:
        return _pyjwt.encode(payload, secret, algorithm="HS256")

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _decode_jwt(token: str, secret: str) -> dict[str, Any]:
    """Decode and verify an HS256 JWT."""
    if _JWT_AVAILABLE and _pyjwt is not None:
        return _pyjwt.decode(token, secret, algorithms=["HS256"])

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token structure")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid JWT signature")

    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    if "exp" in payload and time.time() > payload["exp"]:
        raise ValueError("JWT token expired")

    return payload


class LocalAuthManager:
    """Manages local user accounts and JWT issuance.

    Users are stored in ``{data_dir}/users.json``.
    The JWT signing secret is stored in the AtlasOS secrets manager.
    """

    _JWT_SECRET_KEY = "atlas_jwt_secret"

    def __init__(
        self,
        data_dir: str | Path = "./data",
        token_expire_seconds: int = _ACCESS_TOKEN_EXPIRE_SECONDS,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._users_file = self._data_dir / "users.json"
        self._revoked_file = self._data_dir / "revoked_tokens.json"
        self._token_expire = token_expire_seconds
        self._jwt_secret: str = self._get_or_create_jwt_secret()
        self._users: dict[str, UserRecord] = {}
        self._revoked_jtis: dict[str, float] = {}
        self._load_users()
        self._load_revoked_tokens()

    # ------------------------------------------------------------------
    # JWT secret management
    # ------------------------------------------------------------------

    def _get_or_create_jwt_secret(self) -> str:
        """Get or create the JWT signing secret via secrets manager."""
        try:
            from atlas.secrets import get_secrets_manager
            mgr = get_secrets_manager()
            mgr.initialize()
            existing = mgr.get_secret(self._JWT_SECRET_KEY)
            if existing:
                return existing
            new_secret = secrets.token_urlsafe(64)
            mgr.set_secret(self._JWT_SECRET_KEY, new_secret)
            logger.info("Generated new JWT signing secret")
            return new_secret
        except Exception as exc:
            logger.warning(
                "Could not use secrets manager for JWT secret (%s). "
                "Using ephemeral secret — tokens will be invalidated on restart.",
                exc,
            )
            return secrets.token_urlsafe(64)

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def _load_users(self) -> None:
        """Load users from disk."""
        if not self._users_file.exists():
            logger.debug("No users file found; starting with empty user store")
            return
        try:
            data = json.loads(self._users_file.read_text(encoding="utf-8"))
            self._users = {
                username: UserRecord(**record)
                for username, record in data.items()
            }
            logger.debug("Loaded %d users from disk", len(self._users))
        except Exception as exc:
            logger.error("Failed to load users: %s", exc)

    def _save_users(self) -> None:
        """Persist users to disk."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            data = {u: r.model_dump() for u, r in self._users.items()}
            self._users_file.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.error("Failed to save users: %s", exc)

    def create_user(
        self,
        username: str,
        password: str,
        role: Role = Role.USER,
    ) -> User:
        """Create a new local user.

        Args:
            username: Unique username.
            password: Plain-text password (hashed immediately; never stored).
            role:     ``Role.USER`` or ``Role.ADMIN``.

        Raises:
            ValueError: If username already exists or password is too short.
        """
        if username in self._users:
            raise ValueError(f"User '{username}' already exists")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        record = UserRecord(
            username=username,
            password_hash=_hash_password(password),
            role=role,
        )
        self._users[username] = record
        self._save_users()
        logger.info("Created user '%s' with role %s", username, role.value)
        return User(username=username, role=role)

    def delete_user(self, username: str) -> bool:
        """Delete a user. Returns True if deleted."""
        if username not in self._users:
            return False
        del self._users[username]
        self._save_users()
        logger.info("Deleted user '%s'", username)
        return True

    def change_password(self, username: str, new_password: str) -> bool:
        """Update password for an existing user."""
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters")
        record = self._users.get(username)
        if not record:
            return False
        record.password_hash = _hash_password(new_password)
        self._save_users()
        return True

    def get_user(self, username: str) -> User | None:
        """Return user info (without password hash)."""
        record = self._users.get(username)
        if not record:
            return None
        return User(username=record.username, role=record.role, is_active=record.is_active)

    def list_users(self) -> list[dict[str, Any]]:
        """List all users (without password hashes)."""
        return [
            {"username": r.username, "role": r.role.value, "is_active": r.is_active}
            for r in self._users.values()
        ]

    def ensure_default_admin(self) -> str | None:
        """Create a default admin user if no users exist.

        Returns the generated password so the caller can display it once.
        Returns None if users already exist.
        """
        if self._users:
            return None
        password = secrets.token_urlsafe(16)
        self.create_user("admin", password, Role.ADMIN)
        logger.warning(
            "Created default admin user. Change the password immediately: "
            "username=admin password=%s", password
        )
        return password

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, request: LoginRequest) -> TokenResponse | None:
        """Validate credentials and return a JWT token on success.

        Returns ``None`` if credentials are invalid.
        """
        record = self._users.get(request.username)
        if not record or not record.is_active:
            # Constant-time dummy verification
            _verify_password(request.password, _hash_password("dummy"))
            logger.warning("Authentication failed for user '%s'", request.username)
            return None

        if not _verify_password(request.password, record.password_hash):
            logger.warning("Authentication failed for user '%s'", request.username)
            return None

        token = self._issue_token(record)
        logger.info("User '%s' authenticated successfully", request.username)
        return token

    def _issue_token(self, record: UserRecord) -> TokenResponse:
        """Issue a signed JWT for the given user record."""
        now = time.time()
        claims = JWTClaims(
            sub=record.username,
            role=record.role.value,
            exp=now + self._token_expire,
            iat=now,
            jti=str(uuid.uuid4()),
        )
        token_str = _encode_jwt(claims.to_dict(), self._jwt_secret)
        return TokenResponse(
            access_token=token_str,
            token_type="bearer",
            expires_in=self._token_expire,
        )

    def _load_revoked_tokens(self) -> None:
        """Load persistent revoked tokens from disk and prune expired ones."""
        revoked_file = getattr(self, "_revoked_file", None)
        if not revoked_file or not revoked_file.exists():
            return
        try:
            data = json.loads(revoked_file.read_text(encoding="utf-8"))
            now = time.time()
            self._revoked_jtis = {
                jti: exp
                for jti, exp in data.items()
                if isinstance(exp, (int, float)) and exp > now
            }
            _revoked_jtis.clear()
            _revoked_jtis.update(self._revoked_jtis.keys())
        except Exception as exc:
            logger.debug("Failed to load revoked tokens: %s", exc)

    def _save_revoked_tokens(self) -> None:
        """Persist active revoked tokens to disk, pruning expired ones."""
        revoked_file = getattr(self, "_revoked_file", None)
        if revoked_file is None:
            data_dir = getattr(self, "_data_dir", None)
            if data_dir is not None:
                revoked_file = Path(data_dir) / "revoked_tokens.json"
                self._revoked_file = revoked_file
            else:
                return
        try:
            revoked_file.parent.mkdir(parents=True, exist_ok=True)
            now = time.time()
            revoked_jtis = getattr(self, "_revoked_jtis", {})
            self._revoked_jtis = {
                jti: exp
                for jti, exp in revoked_jtis.items()
                if exp > now
            }
            revoked_file.write_text(
                json.dumps(self._revoked_jtis, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.debug("Failed to save revoked tokens: %s", exc)

    def validate_token(self, token: str) -> User | None:
        """Validate a JWT and return the associated ``User``.

        Returns ``None`` if the token is invalid, expired, or revoked.
        """
        try:
            payload = _decode_jwt(token, self._jwt_secret)
        except Exception as exc:
            logger.debug("JWT token invalid: %s", exc)
            return None

        jti = payload.get("jti", "")
        revoked_jtis = getattr(self, "_revoked_jtis", {})
        if jti in revoked_jtis or jti in _revoked_jtis:
            logger.debug("JWT token revoked (jti=%s)", jti)
            return None

        username = payload.get("sub", "")
        record = self._users.get(username)
        if not record or not record.is_active:
            return None

        return User(
            username=username,
            role=Role(payload.get("role", Role.USER.value)),
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke a JWT by its JTI (persisted to disk)."""
        try:
            payload = _decode_jwt(token, self._jwt_secret)
            jti = payload.get("jti")
            exp = payload.get("exp", time.time() + getattr(self, "_token_expire", _ACCESS_TOKEN_EXPIRE_SECONDS))
            if jti:
                if not hasattr(self, "_revoked_jtis"):
                    self._revoked_jtis = {}
                self._revoked_jtis[jti] = float(exp)
                _revoked_jtis.add(jti)
                self._save_revoked_tokens()
                return True
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Global instance (lazily created)
# ---------------------------------------------------------------------------
_auth_manager: LocalAuthManager | None = None


def get_local_auth_manager(data_dir: str | Path = "./data") -> LocalAuthManager:
    """Get (or lazily create) the global LocalAuthManager."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = LocalAuthManager(data_dir)
    return _auth_manager
