"""Effect instances API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, status as http_status

from ...models import EffectInstance, EffectInfo
from ...storage.pedalboard_store import PedalboardStore
from ...effects.registry import EffectsRegistry
from ...utils.mod_host_client import ModHostClient
from ..dependencies import get_pedalboard_store, get_effects_registry, get_mod_host_client
from ..utils import get_pedalboard_or_404, get_effect_or_404


router = APIRouter()


@router.get("/effects")
async def list_effects(registry: EffectsRegistry = Depends(get_effects_registry)) -> list[EffectInfo]:
    """List all available effects in the system.

    Returns the catalog of effect types that can be instantiated.

    Returns:
        List of effect info objects.
    """
    return registry.get_all()


@router.get("/effects/{uri:path}")
async def get_effect(
    uri: str,
    registry: EffectsRegistry = Depends(get_effects_registry)
) -> EffectInfo:
    """Get details for a specific effect by URI.

    Args:
        uri: The full URI of the effect to retrieve.

    Returns:
        EffectInfo with full details including ports and parameters.

    Raises:
        HTTPException: 404 if effect URI is not found in system.
    """
    effect = registry.get(uri)
    if not effect:
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect not available", "code": "EFFECT_NOT_AVAILABLE"}
        )
    return effect


@router.post("/pedalboards/{pedalboard_id}/effects", status_code=http_status.HTTP_201_CREATED)
async def create_effect_instance(
    pedalboard_id: int,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store),
    registry: EffectsRegistry = Depends(get_effects_registry),
    client: ModHostClient = Depends(get_mod_host_client)
) -> EffectInstance:
    """Add an effect instance to a pedalboard.

    Instantiates the plugin in mod-host and records it in the pedalboard state.

    Args:
        pedalboard_id: The ID of the pedalboard to add the effect to.
        request: JSON body with 'effect_uri' and optional 'name'.

    Returns:
        The created effect instance with ID.

    Raises:
        HTTPException: 404 if pedalboard or effect URI not found.
        HTTPException: 500 if plugin instantiation fails.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)

    effect_uri = request.get("effect_uri")
    if not effect_uri or not registry.get(effect_uri):
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect not available", "code": "EFFECT_NOT_AVAILABLE"}
        )

    # Generate globally unique instance ID (mod-host requires uniqueness across all pedalboards)
    instance_id = store.allocate_effect_instance_id()

    # Add to mod-host
    add_status = client.add_plugin(effect_uri, instance_id)
    if add_status < 0:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to add plugin (code: {add_status})", "code": "PLUGIN_ERROR"}
        )

    effect_info = registry.get(effect_uri)

    # Initialize parameters with default values from EffectInfo
    parameters = {}
    for param_name, param_def in effect_info.parameters.items():
        if param_def.type == "number":
            from mod_api.models.parameter import NumberParameter
            parameters[param_name] = NumberParameter(
                name=param_def.name,
                type=param_def.type,
                min=param_def.min,
                max=param_def.max,
                default=param_def.default,
                value=param_def.default
            )
        else:
            from mod_api.models.parameter import FilenameParameter
            parameters[param_name] = FilenameParameter(
                name=param_def.name,
                type=param_def.type,
                default=param_def.default,
                value=param_def.default
            )

    effect_instance = EffectInstance(
        id=instance_id,
        uri=effect_uri,
        name=request.get("name"),
        ports=effect_info.ports,
        parameters=parameters
    )

    pb.effects[instance_id] = effect_instance
    store._save_pedalboard(pb)

    return effect_instance


@router.get("/pedalboards/{pedalboard_id}/effects")
async def list_effect_instances(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
) -> dict[int, EffectInstance]:
    """List all effect instances on a pedalboard.

    Args:
        pedalboard_id: The ID of the pedalboard.

    Returns:
        Dictionary mapping effect instance IDs to EffectInstance objects.

    Raises:
        HTTPException: 404 if pedalboard doesn't exist.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)
    return {instance_id: effect for instance_id, effect in pb.effects.items()}


@router.delete("/pedalboards/{pedalboard_id}/effects/{effect_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def remove_effect_instance(
    pedalboard_id: int,
    effect_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """Remove an effect instance and all its connections.

    Removes the plugin from mod-host and updates pedalboard state.

    Args:
        pedalboard_id: The ID of the pedalboard.
        effect_id: The instance ID of the effect to remove.

    Raises:
        HTTPException: 404 if pedalboard or effect instance doesn't exist.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)
    effect = get_effect_or_404(pb, effect_id)

    # Remove from mod-host
    client.remove_plugin(effect_id)

    # Remove effect and related connections
    del pb.effects[effect_id]
    # Filter connections that involve this effect's ports (e.g., "effect_0:input" -> effect_0)
    pb.connections = {
        cid: conn for cid, conn in pb.connections.items()
        if f"effect_{effect_id}:" not in conn.input_port_id and f"effect_{effect_id}:" not in conn.output_port_id
    }

    store._save_pedalboard(pb)