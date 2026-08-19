"""Dependency injection for API routes."""

from fastapi import Request

from ..storage.pedalboard_store import PedalboardStore
from ..effects.registry import EffectsRegistry
from ..utils.mod_host_client import ModHostClient


def get_pedalboard_store(request: Request) -> PedalboardStore:
    """Get the pedalboard store instance.

    Returns the PedalboardStore from app state.
    Must be called within a request context.

    Returns:
        PedalboardStore instance.
    """
    return request.app.state.pedalboard_store


def get_effects_registry(request: Request) -> EffectsRegistry:
    """Get the effects registry instance.

    Returns the EffectsRegistry from app state.
    Must be called within a request context.

    Returns:
        EffectsRegistry instance.
    """
    return request.app.state.effects_registry


def get_mod_host_client(request: Request) -> ModHostClient:
    """Get the mod-host client instance.

    Returns the ModHostClient from app state.
    Must be called within a request context.

    Returns:
        ModHostClient instance.
    """
    return request.app.state.mod_host_client