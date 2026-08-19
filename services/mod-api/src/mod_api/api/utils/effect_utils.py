"""Utility functions for effect operations."""

from fastapi import HTTPException

EFFECT_INSTANCE_NOT_FOUND = "EFFECT_INSTANCE_NOT_FOUND"


def get_effect_or_404(pb, effect_id: int):
    """Get an effect instance from a pedalboard or raise 404.

    Args:
        pb: The Pedalboard instance.
        effect_id: The ID of the effect instance to retrieve.

    Returns:
        The EffectInstance.

    Raises:
        HTTPException: 404 if effect instance doesn't exist.
    """
    effect = pb.effects.get(effect_id)
    if not effect:
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect instance not found", "code": EFFECT_INSTANCE_NOT_FOUND}
        )
    return effect