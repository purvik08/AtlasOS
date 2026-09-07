"""Auth data models for Atlas OS local authentication system."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    """User role for authorization.

    Design note: roles are intentionally simple for v1.3.0.
    OAuth/OIDC can be layered on top in v1.4.0 without changing
    the existing authorization logic (which only checks ``Role``).
    """
    USER = "user"
    ADMIN = "admin"


class User(BaseModel):
    """A local Atlas OS user."""
    username: str
    role: Role = Role.USER
    is_active: bool = True

    def has_role(self, required: Role) -> bool:
        """Return True if this user has ``required`` role or higher."""
        role_order = {Role.USER: 0, Role.ADMIN: 1}
        return role_order.get(self.role, 0) >= role_order.get(required, 0)


class UserRecord(BaseModel):
    """Stored user record (includes hashed password)."""
    username: str
    password_hash: str          # bcrypt hash
    role: Role = Role.USER
    is_active: bool = True


class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int             # seconds


class JWTClaims(BaseModel):
    """JWT claims we encode/decode."""
    sub: str                    # username
    role: str                   # Role.value
    exp: float                  # expiry timestamp
    iat: float                  # issued-at timestamp
    jti: str                    # JWT ID (for revocation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub": self.sub,
            "role": self.role,
            "exp": self.exp,
            "iat": self.iat,
            "jti": self.jti,
        }
