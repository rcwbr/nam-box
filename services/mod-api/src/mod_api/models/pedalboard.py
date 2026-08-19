"""Pedalboard data model."""

from __future__ import annotations

from pydantic import BaseModel

from .connection import Connection
from .effect_instance import EffectInstance


class Pedalboard(BaseModel):
    """Represents a complete pedalboard configuration.

    A pedalboard contains effect instances and their connections.
    Parameter values live inside each effect's parameters field.

    Attributes:
        id: The unique pedalboard identifier.
        name: Human-readable pedalboard name.
        file: JSON filename for persistence (derived from name).
        effects: Dict of effect instances keyed by instance ID.
        connections: Dict of connections keyed by connection ID.
    """

    id: int
    name: str
    file: str  # Derived from name: name.lower().replace(' ', '-') + '.json'
    effects: dict[int, EffectInstance] = {}
    connections: dict[int, Connection] = {}