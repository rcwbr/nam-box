"""Port management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends

from ...models import Port, PortType
from ...storage.pedalboard_store import PedalboardStore
from ...utils.mod_host_client import ModHostClient
from ..dependencies import get_pedalboard_store, get_mod_host_client
from ..utils import get_pedalboard_or_404


router = APIRouter()


@router.get("/pedalboards/{pedalboard_id}/ports")
async def list_ports(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
) -> list[Port]:
    """List all ports available on the pedalboard.

    Combines effect instance ports with system ports (input/output jacks).
    System ports are discovered from JACK configuration.

    Args:
        pedalboard_id: The ID of the pedalboard.
        store: Pedalboard store for pedalboard data.
        client: Mod-host client for system port discovery.

    Returns:
        List of Port objects including system and effect ports.

    Raises:
        HTTPException: 404 if pedalboard doesn't exist.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)

    ports: list[Port] = []

    # Discover available system ports from JACK configuration
    _, enumerate_results = client.enumerate()

    # System ports are identified by "system:" prefix in enumerate output
    system_ports = {item for item in enumerate_results if item.startswith("system:")}

    for port_id in sorted(system_ports):
        port_type = PortType.INPUT if "capture" in port_id else PortType.OUTPUT
        ports.append(Port(
            name=port_id.split(":", 1)[-1],
            type=port_type,
            owner_type="system"
        ))

    # Add effect instance ports from pedalboard state
    for effect_id, effect in pb.effects.items():
        for port in effect.ports:
            ports.append(Port(
                name=port.name,
                type=port.type,
                owner_type="effect",
                effect_instance_id=effect_id
            ))

    return ports