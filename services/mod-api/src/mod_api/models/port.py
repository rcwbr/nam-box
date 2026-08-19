"""Port models for audio/MIDI routing."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class PortType(str, Enum):
    """Enumeration of port types."""

    INPUT = "input"
    OUTPUT = "output"
    MIDI_IN = "midi_in"
    MIDI_OUT = "midi_out"


class Port(BaseModel):
    """Port representation for audio/MIDI routing.

    Attributes:
        name: Human-readable port name.
        type: The type of port (input/output/midi_in/midi_out).
        owner_type: Either 'system' or 'effect'.
        effect_instance_id: The effect instance ID if owner_type is 'effect', None otherwise.
    """

    name: str
    type: str
    owner_type: str | None = None
    effect_instance_id: int | None = None