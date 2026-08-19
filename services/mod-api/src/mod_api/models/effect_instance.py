"""Effect instance model for pedalboard effect placements."""


from pydantic import BaseModel

from .effect_info import EffectInfo
from .parameter import Parameter


class EffectInstance(EffectInfo):
    """Represents an instantiated effect plugin on a pedalboard.

    Inherits from EffectInfo for ports and other metadata, but overrides parameters
    to store current values instead of definitions.

    Attributes:
        id: Unique identifier for this effect instance.
        uri: Full URI of the LV2 plugin.
        name: Optional human-readable name for the instance.
        ports: List of Port objects (inherited from EffectInfo).
        parameters: Dictionary mapping parameter names to Parameter objects with values.
    """

    id: int = 0
    parameters: dict[str, Parameter] = {}