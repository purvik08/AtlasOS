"""Unit tests for JWT validation and FastAPI middleware."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request

from atlas.auth.manager import LocalAuthManager
from atlas.auth.middleware import get_current_user, require_admin, require_role
from atlas.auth.models import Role, User


class TestMiddleware:
    """Test get_current_user and role-checking dependencies."""

    def test_missing_auth_header_raises_401(self):
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_invalid_bearer_format_raises_401(self):
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Basic 12345"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_uninitialized_auth_manager_raises_503(self):
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer some-token"}
        request.app.state.local_auth_manager = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 503

    def test_invalid_token_raises_401(self):
        auth_mgr = MagicMock(spec=LocalAuthManager)
        auth_mgr.validate_token.return_value = None

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer bad-token"}
        request.app.state.local_auth_manager = auth_mgr

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_valid_token_returns_user(self):
        auth_mgr = MagicMock(spec=LocalAuthManager)
        auth_mgr.validate_token.return_value = User(username="admin", role=Role.ADMIN)

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer good-token"}
        request.app.state.local_auth_manager = auth_mgr

        user = get_current_user(request)
        assert user.username == "admin"
        assert user.role == Role.ADMIN

    def test_require_role_admin_success(self):
        admin_user = User(username="admin", role=Role.ADMIN)
        check = require_role(Role.ADMIN)
        result = check(user=admin_user)
        assert result == admin_user

    def test_require_role_admin_forbidden_for_regular_user(self):
        reg_user = User(username="regular", role=Role.USER)
        check = require_role(Role.ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            check(user=reg_user)
        assert exc_info.value.status_code == 403

    def test_require_role_user_allows_admin_and_user(self):
        check = require_role(Role.USER)
        admin_user = User(username="admin", role=Role.ADMIN)
        reg_user = User(username="regular", role=Role.USER)

        assert check(user=admin_user) == admin_user
        assert check(user=reg_user) == reg_user
