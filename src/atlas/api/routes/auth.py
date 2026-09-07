"""Authentication routes for Atlas OS API.

POST /v1/auth/login    — exchange username+password for JWT
POST /v1/auth/refresh  — refresh a valid JWT
POST /v1/auth/logout   — revoke a JWT (in-process)
GET  /v1/auth/me       — return current user info
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from atlas.auth.middleware import get_current_user
from atlas.auth.models import LoginRequest, Role, TokenResponse, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, body: LoginRequest) -> TokenResponse:
    """Authenticate with username and password. Returns a JWT access token."""
    auth_mgr = getattr(request.app.state, "local_auth_manager", None)
    if auth_mgr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialised",
        )

    token = auth_mgr.authenticate(body)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.post("/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Revoke the current JWT. The token will be invalid immediately."""
    authorization = request.headers.get("Authorization", "")
    token = authorization[7:] if authorization.startswith("Bearer ") else ""

    auth_mgr = getattr(request.app.state, "local_auth_manager", None)
    if auth_mgr and token:
        auth_mgr.revoke_token(token)

    return {"detail": f"User '{user.username}' logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    user: User = Depends(get_current_user),
) -> TokenResponse:
    """Issue a new JWT for the currently authenticated user."""
    auth_mgr = getattr(request.app.state, "local_auth_manager", None)
    if auth_mgr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialised",
        )

    # Retrieve the stored record to re-issue
    from atlas.auth.models import UserRecord
    record = auth_mgr._users.get(user.username)  # type: ignore[union-attr]
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return auth_mgr._issue_token(record)  # type: ignore[union-attr]


@router.get("/me", response_model=dict)
async def me(user: User = Depends(get_current_user)) -> dict:
    """Return the currently authenticated user's info."""
    return {
        "username": user.username,
        "role": user.role.value,
        "is_active": user.is_active,
    }


@router.post("/users")
async def create_user(
    request: Request,
    body: dict,
    user: User = Depends(get_current_user),
) -> dict:
    """Create a new user (admin only)."""
    from atlas.auth.middleware import require_role
    from atlas.auth.models import Role

    if not user.has_role(Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to create users",
        )

    auth_mgr = getattr(request.app.state, "local_auth_manager", None)
    if auth_mgr is None:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    username = body.get("username", "")
    password = body.get("password", "")
    role_str = body.get("role", "user")

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    try:
        role = Role(role_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role_str}")

    try:
        new_user = auth_mgr.create_user(username, password, role)
        return {"username": new_user.username, "role": new_user.role.value}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
