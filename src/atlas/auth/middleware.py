"""FastAPI auth middleware and authorization dependencies.

Provides:
- ``get_current_user``  — extracts and validates JWT from Authorization header
- ``require_role(role)`` — requires a minimum role
- ``require_admin``      — shortcut for ``require_role(Role.ADMIN)``

Existing API key auth (``require_auth`` in ``atlas.api.auth``) is preserved
and unmodified. This module adds JWT-based user auth on top.

Architecture allows OAuth/OIDC to replace ``get_current_user`` in v1.4.0
without touching the ``require_role``/``require_admin`` authorization layer.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from atlas.auth.models import Role, User


def get_current_user(request: Request) -> User:
    """FastAPI dependency: extract and validate JWT, return User.

    Reads the ``Authorization: Bearer <token>`` header.
    Raises HTTP 401 if missing or invalid.
    """
    authorization: str | None = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = parts[1].strip()

    auth_mgr = getattr(request.app.state, "local_auth_manager", None)
    if auth_mgr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialised",
        )

    user = auth_mgr.validate_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(required_role: Role) -> Callable[..., User]:
    """Return a FastAPI dependency that requires at least ``required_role``.

    Usage::

        @router.post("/admin/action")
        async def admin_action(user: User = Depends(require_role(Role.ADMIN))):
            ...
    """
    def _check(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions. "
                    f"Required role: {required_role.value}, "
                    f"your role: {user.role.value}"
                ),
            )
        return user
    return _check


# Convenience alias for admin-only endpoints
require_admin: Callable[..., User] = require_role(Role.ADMIN)
