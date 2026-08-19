"""Utility functions for pedalboard operations."""

from fastapi import HTTPException

from ...storage.pedalboard_store import PedalboardStore

PEDALBOARD_NOT_FOUND = "PEDALBOARD_NOT_FOUND"


def get_pedalboard_or_404(store: PedalboardStore, pedalboard_id: int):
    """Get a pedalboard by ID or raise 404.

    Args:
        store: The pedalboard store instance.
        pedalboard_id: The ID of the pedalboard to retrieve.

    Returns:
        The Pedalboard instance.

    Raises:
        HTTPException: 404 if pedalboard doesn't exist.
    """
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": PEDALBOARD_NOT_FOUND}
        )
    return pb