"""Pedalboard API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, status as http_status

from ...models import Pedalboard
from ...storage.pedalboard_store import PedalboardStore
from ..dependencies import get_pedalboard_store
from ..utils import get_pedalboard_or_404


router = APIRouter(prefix="/pedalboards")


@router.get("")
async def list_pedalboards(store: PedalboardStore = Depends(get_pedalboard_store)) -> dict[int, Pedalboard]:
    """List all available pedalboards with metadata.

    Returns a dict of all pedalboards keyed by ID.

    Returns:
        Dict mapping pedalboard IDs to Pedalboard objects.
    """
    result: dict[int, Pedalboard] = {}
    for pb_id, pb in store._pedalboards.items():
        result[pb_id] = pb
    return result


@router.get("/current")
async def get_current_pedalboard(store: PedalboardStore = Depends(get_pedalboard_store)):
    """Get the current pedalboard.

    Returns full details of the currently selected pedalboard.

    Returns:
        Pedalboard object if a current pedalboard exists.
    """
    if not store._current_id or store._current_id not in store._pedalboards:
        return None

    return store._pedalboards[store._current_id]


@router.get("/{pedalboard_id}")
async def get_pedalboard(pedalboard_id: int, store: PedalboardStore = Depends(get_pedalboard_store)) -> Pedalboard:
    """Get full details of a specific pedalboard.

    Args:
        pedalboard_id: The ID of the pedalboard to retrieve.

    Returns:
        Pedalboard object with all effects and connections.

    Raises:
        HTTPException: 404 if pedalboard ID doesn't exist.
    """
    return get_pedalboard_or_404(store, pedalboard_id)


@router.post("", status_code=http_status.HTTP_201_CREATED)
async def create_pedalboard(
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store)
) -> Pedalboard:
    """Create a new pedalboard.

    Can create empty or as a duplicate of the current board.

    Args:
        request: JSON body with 'name' and optional 'duplicate_current'.

    Returns:
        The newly created pedalboard.

    Raises:
        HTTPException: 400 if request body is malformed.
    """
    name = request.get("name")
    if not name:
        raise HTTPException(
            status_code=400,
            detail={"error": "Name required", "code": "INVALID_REQUEST"}
        )

    duplicate_current = request.get("duplicate_current", False)
    source_id = store._current_id if duplicate_current else None

    pedalboard = store.create(name, duplicate_from_id=source_id)
    store._current_id = pedalboard.id
    return pedalboard


@router.delete("/{pedalboard_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_pedalboard(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """Delete a pedalboard.

    If deleting the current pedalboard, no pedalboard will be current
    until a new one is selected.

    Args:
        pedalboard_id: The ID of the pedalboard to delete.

    Raises:
        HTTPException: 404 if pedalboard ID doesn't exist.
    """
    get_pedalboard_or_404(store, pedalboard_id)

    if store._current_id == pedalboard_id:
        store._current_id = None

    store.delete(pedalboard_id)


@router.put("/{pedalboard_id}/select", status_code=http_status.HTTP_200_OK)
async def select_pedalboard(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """Select a pedalboard to make it the current one.

    Args:
        pedalboard_id: The ID of the pedalboard to select.

    Raises:
        HTTPException: 404 if pedalboard ID doesn't exist.
    """
    get_pedalboard_or_404(store, pedalboard_id)

    store._current_id = pedalboard_id


@router.put("/{pedalboard_id}/rename", status_code=http_status.HTTP_200_OK)
async def rename_pedalboard(
    pedalboard_id: int,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store)
) -> Pedalboard:
    """Rename a pedalboard.

    Args:
        pedalboard_id: The ID of the pedalboard to rename.
        request: JSON body with 'name' field.

    Returns:
        The renamed pedalboard.

    Raises:
        HTTPException: 404 if pedalboard ID doesn't exist.
        HTTPException: 400 if name is missing or invalid.
    """
    name = request.get("name")
    if not name:
        raise HTTPException(
            status_code=400,
            detail={"error": "Name required", "code": "INVALID_REQUEST"}
        )

    pb = store.rename(pedalboard_id, name)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    return pb