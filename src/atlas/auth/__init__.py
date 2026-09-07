"""Atlas OS auth module — local JWT authentication and RBAC authorization.

v1.3.0: Local authentication (JWT + bcrypt).
v1.4.0: OAuth/OIDC can be added by replacing LocalAuthManager without
        changing the middleware/authorization layer.
"""

from __future__ import annotations

from atlas.auth.manager import LocalAuthManager, get_local_auth_manager
from atlas.auth.middleware import get_current_user, require_admin, require_role
from atlas.auth.models import (
    JWTClaims,
    LoginRequest,
    Role,
    TokenResponse,
    User,
    UserRecord,
)

__all__ = [
    "LocalAuthManager",
    "get_local_auth_manager",
    "get_current_user",
    "require_role",
    "require_admin",
    "Role",
    "User",
    "UserRecord",
    "LoginRequest",
    "TokenResponse",
    "JWTClaims",
]
