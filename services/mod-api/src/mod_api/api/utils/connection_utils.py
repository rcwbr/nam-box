"""Utility functions for connection operations."""

from fastapi import HTTPException

CONNECTION_NOT_FOUND = "CONNECTION_NOT_FOUND"


def get_connection_or_404(pb, connection_id: int):
    """Get a connection from a pedalboard or raise 404.

    Args:
        pb: The Pedalboard instance.
        connection_id: The ID of the connection to retrieve.

    Returns:
        The Connection instance.

    Raises:
        HTTPException: 404 if connection doesn't exist.
    """
    connection = pb.connections.get(connection_id)
    if not connection:
        raise HTTPException(
            status_code=404,
            detail={"error": "Connection not found", "code": CONNECTION_NOT_FOUND}
        )
    return connection