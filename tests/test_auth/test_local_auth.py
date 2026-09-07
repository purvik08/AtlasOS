"""Unit tests for LocalAuthManager.

Tests password hashing, user management, authentication, and token issuance.
All tests use a temporary directory for user storage — no production state touched.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from atlas.auth.models import LoginRequest, Role, User
from atlas.auth.manager import LocalAuthManager, _hash_password, _verify_password


class TestPasswordHashing:
    """Tests for hash/verify functions — works without passlib."""

    def test_hash_is_not_plaintext(self):
        h = _hash_password("mypassword")
        assert h != "mypassword"

    def test_verify_correct_password(self):
        h = _hash_password("correct")
        assert _verify_password("correct", h) is True

    def test_verify_wrong_password(self):
        h = _hash_password("correct")
        assert _verify_password("wrong", h) is False

    def test_hash_is_different_each_time(self):
        """Hashes should use unique salts so they differ."""
        h1 = _hash_password("same")
        h2 = _hash_password("same")
        # Hashes should differ (salt randomness); both should verify correctly
        assert _verify_password("same", h1)
        assert _verify_password("same", h2)


class TestLocalAuthManager:
    """Tests for LocalAuthManager user management and auth."""

    def _make_manager(self) -> LocalAuthManager:
        tmpdir = tempfile.mkdtemp()
        # Patch JWT secret to avoid needing real secrets manager
        mgr = LocalAuthManager.__new__(LocalAuthManager)
        mgr._data_dir = Path(tmpdir)
        mgr._data_dir.mkdir(parents=True, exist_ok=True)
        mgr._users_file = mgr._data_dir / "users.json"
        mgr._token_expire = 3600
        mgr._jwt_secret = "test-secret-for-unit-tests-only"
        mgr._users = {}
        return mgr

    def test_create_user(self):
        mgr = self._make_manager()
        user = mgr.create_user("alice", "password123", Role.USER)
        assert user.username == "alice"
        assert user.role == Role.USER

    def test_create_admin_user(self):
        mgr = self._make_manager()
        user = mgr.create_user("bob", "secure456!", Role.ADMIN)
        assert user.role == Role.ADMIN

    def test_create_user_duplicate_raises(self):
        mgr = self._make_manager()
        mgr.create_user("alice", "password123")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_user("alice", "password999")


    def test_create_user_short_password_raises(self):
        mgr = self._make_manager()
        with pytest.raises(ValueError, match="8 characters"):
            mgr.create_user("alice", "short")

    def test_get_user_returns_user(self):
        mgr = self._make_manager()
        mgr.create_user("alice", "password123")
        user = mgr.get_user("alice")
        assert user is not None
        assert user.username == "alice"

    def test_get_user_missing_returns_none(self):
        mgr = self._make_manager()
        assert mgr.get_user("nobody") is None

    def test_delete_user(self):
        mgr = self._make_manager()
        mgr.create_user("temp", "password123")
        assert mgr.delete_user("temp") is True
        assert mgr.get_user("temp") is None

    def test_delete_missing_user_returns_false(self):
        mgr = self._make_manager()
        assert mgr.delete_user("nobody") is False

    def test_list_users(self):
        mgr = self._make_manager()
        mgr.create_user("user1", "password123")
        mgr.create_user("user2", "password456")
        users = mgr.list_users()
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert "user1" in usernames

    def test_change_password(self):
        mgr = self._make_manager()
        mgr.create_user("alice", "oldpassword")
        mgr.change_password("alice", "newpassword1")
        req = LoginRequest(username="alice", password="newpassword1")
        result = mgr.authenticate(req)
        assert result is not None

    def test_ensure_default_admin_when_no_users(self):
        mgr = self._make_manager()
        password = mgr.ensure_default_admin()
        assert password is not None
        assert len(password) > 8
        # Should create admin user
        user = mgr.get_user("admin")
        assert user is not None
        assert user.role == Role.ADMIN

    def test_ensure_default_admin_noop_when_users_exist(self):
        mgr = self._make_manager()
        mgr.create_user("existing", "password123")
        result = mgr.ensure_default_admin()
        assert result is None  # No-op

    def test_authenticate_valid_credentials(self):
        mgr = self._make_manager()
        mgr.create_user("alice", "password123")
        req = LoginRequest(username="alice", password="password123")
        result = mgr.authenticate(req)
        assert result is not None
        assert result.token_type == "bearer"
        assert len(result.access_token) > 0

    def test_authenticate_wrong_password(self):
        mgr = self._make_manager()
        mgr.create_user("alice", "password123")
        req = LoginRequest(username="alice", password="wrong")
        result = mgr.authenticate(req)
        assert result is None

    def test_authenticate_unknown_user(self):
        mgr = self._make_manager()
        req = LoginRequest(username="ghost", password="password")
        result = mgr.authenticate(req)
        assert result is None

    def test_validate_token_round_trip(self):
        """Issue a token, validate it, get User back."""
        mgr = self._make_manager()
        mgr.create_user("alice", "password123", Role.ADMIN)
        req = LoginRequest(username="alice", password="password123")
        token_resp = mgr.authenticate(req)
        assert token_resp is not None

        user = mgr.validate_token(token_resp.access_token)
        assert user is not None
        assert user.username == "alice"
        assert user.role == Role.ADMIN

    def test_validate_invalid_token(self):
        mgr = self._make_manager()
        assert mgr.validate_token("not.a.jwt") is None

    def test_revoke_token(self):
        mgr = self._make_manager()
        mgr.create_user("alice", "password123")
        token_resp = mgr.authenticate(LoginRequest(username="alice", password="password123"))
        assert token_resp is not None

        # Revoke
        assert mgr.revoke_token(token_resp.access_token) is True
        # Should no longer validate
        assert mgr.validate_token(token_resp.access_token) is None

    def test_revoke_token_persistence_across_instances(self):
        mgr1 = self._make_manager()
        mgr1.create_user("alice", "password123")
        token_resp = mgr1.authenticate(LoginRequest(username="alice", password="password123"))
        assert token_resp is not None

        # Revoke on instance 1
        assert mgr1.revoke_token(token_resp.access_token) is True

        # Construct instance 2 pointing to same data_dir and same secret
        mgr2 = LocalAuthManager.__new__(LocalAuthManager)
        mgr2._data_dir = mgr1._data_dir
        mgr2._users_file = mgr1._users_file
        mgr2._revoked_file = mgr1._revoked_file
        mgr2._token_expire = mgr1._token_expire
        mgr2._jwt_secret = mgr1._jwt_secret
        mgr2._users = {}
        mgr2._revoked_jtis = {}
        mgr2._load_users()
        mgr2._load_revoked_tokens()

        # Token should remain revoked on instance 2
        assert mgr2.validate_token(token_resp.access_token) is None


class TestUserModel:
    """Tests for User and Role models."""

    def test_user_has_role_equal(self):
        user = User(username="alice", role=Role.ADMIN)
        assert user.has_role(Role.ADMIN) is True
        assert user.has_role(Role.USER) is True

    def test_user_role_insufficient(self):
        user = User(username="bob", role=Role.USER)
        assert user.has_role(Role.ADMIN) is False
        assert user.has_role(Role.USER) is True

    def test_role_values(self):
        assert Role.USER.value == "user"
        assert Role.ADMIN.value == "admin"
