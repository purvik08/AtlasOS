"""AI provider router for Atlas OS.

The :class:`AIRouter` decouples the rest of the AI Engine from specific
provider implementations.  Given a *role* (``local``, ``cloud``, ``auto``) or
an explicit provider name, the router selects the best available provider.

Routing strategy
----------------
* **Explicit name**: ``router.select(provider_name="gemini")`` returns the
  ``GeminiProvider`` directly, or raises :class:`ProviderNotFoundError`.
* **Role-based (local)**: returns the first registered *LOCAL* provider.
* **Role-based (cloud)**: returns the first registered *CLOUD* provider.
* **Auto**: prefers LOCAL → CLOUD fallback, so the OS stays offline-first.
* **Fallback**: when the preferred provider is unavailable (unhealthy or
  absent), ``select_with_fallback`` tries the next available provider in
  registration order and logs a warning.

SOLID note — the router is *Open/Closed*: new providers are registered via
:meth:`register` without touching routing logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atlas.ai.providers.base import AIProvider, ProviderRole

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ProviderNotFoundError(Exception):
    """Raised when no suitable provider can be found for a request."""


class AIRouter:
    """Selects a provider for each inference request.

    Providers are registered in priority order; the router iterates them
    in that order when performing role-based selection.

    Parameters
    ----------
    default_role:
        Role used when the caller passes ``role=None``.  Defaults to
        ``ProviderRole.AUTO``.
    """

    def __init__(self, default_role: ProviderRole = ProviderRole.AUTO) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._registration_order: list[str] = []
        self._default_role = default_role
        logger.debug("AIRouter initialised with default_role=%s.", default_role.value)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: AIProvider) -> None:
        """Register *provider* with the router.

        Registration order determines priority during role-based selection.
        Registering a provider with the same name twice replaces the first.

        Parameters
        ----------
        provider:
            A fully-initialised :class:`~atlas.ai.providers.base.AIProvider`.
        """
        if provider.name not in self._providers:
            self._registration_order.append(provider.name)
        self._providers[provider.name] = provider
        logger.debug(
            "AIRouter: registered provider '%s' (role=%s).",
            provider.name,
            provider.role.value,
        )

    def unregister(self, name: str) -> None:
        """Remove a provider by name.  Silently ignored if not found."""
        self._providers.pop(name, None)
        try:
            self._registration_order.remove(name)
        except ValueError:
            pass

    def registered_names(self) -> list[str]:
        """Return names of all registered providers in registration order."""
        return list(self._registration_order)

    def get(self, name: str) -> AIProvider:
        """Return a registered provider by exact name.

        Raises
        ------
        ProviderNotFoundError
        """
        try:
            return self._providers[name]
        except KeyError:
            raise ProviderNotFoundError(
                f"Provider '{name}' is not registered. "
                f"Registered: {self.registered_names()}"
            ) from None

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select(
        self,
        *,
        provider_name: str | None = None,
        role: ProviderRole | None = None,
    ) -> AIProvider:
        """Return the best provider for the given constraints.

        Priority:
        1. Explicit *provider_name* — returned directly (or error if unknown).
        2. *role* — first registered provider with that role.
        3. Default role.

        Raises
        ------
        ProviderNotFoundError
            If no suitable provider is available.
        """
        if provider_name is not None:
            return self.get(provider_name)

        effective_role = role if role is not None else self._default_role

        if effective_role is ProviderRole.AUTO:
            return self._select_auto()

        return self._select_by_role(effective_role)

    def select_with_fallback(
        self,
        *,
        provider_name: str | None = None,
        role: ProviderRole | None = None,
    ) -> AIProvider:
        """Like :meth:`select` but falls back to any available provider on failure.

        Useful for non-critical operations (health checks, model listing) where
        *some* response is better than none.

        Raises
        ------
        ProviderNotFoundError
            Only if absolutely no providers are registered.
        """
        try:
            return self.select(provider_name=provider_name, role=role)
        except ProviderNotFoundError:
            logger.warning(
                "AIRouter: primary selection failed (name=%s, role=%s); "
                "falling back to first available provider.",
                provider_name,
                role,
            )
            if self._registration_order:
                fallback = self._providers[self._registration_order[0]]
                logger.warning(
                    "AIRouter: using fallback provider '%s'.", fallback.name
                )
                return fallback
            raise ProviderNotFoundError(
                "No providers are registered. Cannot route request."
            ) from None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _select_by_role(self, role: ProviderRole) -> AIProvider:
        """Return the first registered provider with matching *role*."""
        for name in self._registration_order:
            p = self._providers[name]
            if p.role is role:
                logger.debug("AIRouter: selected '%s' for role=%s.", name, role.value)
                return p
        raise ProviderNotFoundError(
            f"No provider with role '{role.value}' is registered. "
            f"Registered: {self.registered_names()}"
        )

    def _select_auto(self) -> AIProvider:
        """Prefer LOCAL, then CLOUD (offline-first)."""
        for target_role in (ProviderRole.LOCAL, ProviderRole.CLOUD):
            for name in self._registration_order:
                p = self._providers[name]
                if p.role is target_role:
                    logger.debug(
                        "AIRouter (auto): selected '%s' (role=%s).", name, target_role.value
                    )
                    return p
        raise ProviderNotFoundError(
            "No providers available for auto-routing. "
            f"Registered: {self.registered_names()}"
        )

    def __repr__(self) -> str:
        return (
            f"AIRouter(providers={self.registered_names()!r}, "
            f"default_role={self._default_role.value!r})"
        )
