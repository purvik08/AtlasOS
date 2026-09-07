"""Unit tests for plugin permission enforcement."""

from __future__ import annotations

import pytest

from atlas.plugins.permissions import (
    Permission,
    PermissionDeniedError,
    PermissionRegistry,
    check_permission,
    get_permission_registry,
)


class TestPermissionRegistry:
    """Test PermissionRegistry grants, checks, and revocation."""

    def test_register_and_has_permission(self):
        reg = PermissionRegistry()
        reg.register("plugin-a", ["network", "filesystem.read"])

        assert reg.has_permission("plugin-a", Permission.NETWORK) is True
        assert reg.has_permission("plugin-a", Permission.FILESYSTEM_READ) is True
        assert reg.has_permission("plugin-a", Permission.FILESYSTEM_WRITE) is False

    def test_register_unknown_permission_ignored_gracefully(self):
        reg = PermissionRegistry()
        reg.register("plugin-b", ["invalid.permission", "audio"])

        assert reg.has_permission("plugin-b", Permission.AUDIO) is True
        assert len(reg.list_grants("plugin-b")) == 1

    def test_check_raises_permission_denied(self):
        reg = PermissionRegistry()
        reg.register("plugin-c", ["ai.inference"])

        # Allowed
        reg.check("plugin-c", Permission.AI_INFERENCE)

        # Denied
        with pytest.raises(PermissionDeniedError) as exc_info:
            reg.check("plugin-c", Permission.SYSTEM_ADMIN)
        assert "plugin-c" in str(exc_info.value)
        assert "system.admin" in str(exc_info.value)

    def test_unregister_revokes_permissions(self):
        reg = PermissionRegistry()
        reg.register("plugin-d", ["network"])
        assert reg.has_permission("plugin-d", Permission.NETWORK) is True

        reg.unregister("plugin-d")
        assert reg.has_permission("plugin-d", Permission.NETWORK) is False
        assert reg.list_grants("plugin-d") == []


class TestGlobalPermissionHelpers:
    """Test global check_permission function."""

    def test_global_check_permission(self):
        reg = get_permission_registry()
        reg.register("test-global", ["mqtt"])

        check_permission("test-global", Permission.MQTT)

        with pytest.raises(PermissionDeniedError):
            check_permission("test-global", Permission.NETWORK)

        reg.unregister("test-global")
