"""Connection management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, status as http_status

from ...models import Connection
from ...storage.pedalboard_store import PedalboardStore
from ...utils.mod_host_client import ModHostClient
from ..dependencies import get_pedalboard_store, get_mod_host_client
from ..utils import get_pedalboard_or_404, get_connection_or_404


router = APIRouter()


@router.post("/pedalboards/{pedalboard_id}/connections", status_code=http_status.HTTP_201_CREATED)
async def create_connection(
    pedalboard_id: int,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
) -> Connection:
    """Create a connection between an input port and an output port.

    Connects two ports to establish signal flow in the pedalboard.

    Args:
        pedalboard_id: The ID of the pedalboard.
        request: JSON body with 'input_port_id' and 'output_port_id'.

    Returns:
        The created connection with ID.

    Raises:
        HTTPException: 404 if pedalboard or specified port doesn't exist.
        HTTPException: 400 if request body is malformed.
        HTTPException: 500 if port connection fails.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)

    input_port_id = request.get("input_port_id")
    output_port_id = request.get("output_port_id")

    if not input_port_id or not output_port_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "Port IDs required", "code": "INVALID_REQUEST"}
        )

    # Validate ports exist (check both system and effect ports)
    # Discover available ports from JACK configuration
    _, enumerate_results = client.enumerate()

    # Build set of all available ports from system ports and effect ports
    all_ports = set(enumerate_results)  # System ports from JACK config

    # Add effect instance ports from pedalboard state
    for effect_id, effect in pb.effects.items():
        for port in effect.ports:
            all_ports.add(f"effect_{effect_id}:{port.name}")

    if input_port_id not in all_ports or output_port_id not in all_ports:
        raise HTTPException(
            status_code=404,
            detail={"error": "Port not found", "code": "PORT_NOT_FOUND"}
        )

    # Create connection in mod-host
    conn_status = client.connect_ports(input_port_id, output_port_id)
    if conn_status < 0:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to connect ports (code: {conn_status})", "code": "CONNECTION_ERROR"}
        )

    # Create connection record
    connection_id = max(pb.connections.keys(), default=0) + 1
    connection = Connection(
        id=connection_id,
        input_port_id=input_port_id,
        output_port_id=output_port_id
    )

    pb.connections[connection_id] = connection
    store._save_pedalboard(pb)

    return connection


@router.get("/pedalboards/{pedalboard_id}/connections")
async def list_connections(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
) -> dict[int, Connection]:
    """List all connections on a pedalboard.

    Args:
        pedalboard_id: The ID of the pedalboard.

    Returns:
        Dict mapping connection IDs to Connection objects.

    Raises:
        HTTPException: 404 if pedalboard doesn't exist.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)

    return pb.connections


@router.delete("/pedalboards/{pedalboard_id}/connections/{connection_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def remove_connection(
    pedalboard_id: int,
    connection_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """Remove a connection.

    Disconnects the ports in mod-host and removes the connection record.

    Args:
        pedalboard_id: The ID of the pedalboard.
        connection_id: The ID of the connection to remove.

    Raises:
        HTTPException: 404 if pedalboard or connection doesn't exist.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)
    connection = get_connection_or_404(pb, connection_id)

    # Disconnect in mod-host
    client.disconnect_ports(connection.input_port_id, connection.output_port_id)

    # Remove connection record
    del pb.connections[connection_id]
    store._save_pedalboard(pb)