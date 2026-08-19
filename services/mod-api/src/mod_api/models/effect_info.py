"""Effect info model definition."""

from pydantic import BaseModel

from .parameter import ParameterType
from .port import Port


class EffectInfo(BaseModel):
    """Information about an effect/plugin.

    Contains metadata about an LV2 plugin including its URI, name,
    available ports, and parameter definitions (without current values).

    Used for: GET /effects, GET /effects/{uri}
    """

    uri: str
    name: str | None = None
    ports: list[Port] = []
    parameters: dict[str, ParameterType] = {}  # Parameter definitions keyed by name
