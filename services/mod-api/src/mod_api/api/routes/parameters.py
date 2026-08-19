"""Parameter management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, status as http_status

from ...models import Parameter
from ...storage.pedalboard_store import PedalboardStore
from ...utils.mod_host_client import ModHostClient
from ..dependencies import get_pedalboard_store, get_mod_host_client
from ..utils import get_pedalboard_or_404, get_effect_or_404


router = APIRouter()


@router.get("/pedalboards/{pedalboard_id}/effects/{effect_id}/parameters")
async def get_parameters(
    pedalboard_id: int,
    effect_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store),
) -> dict[str, Parameter]:
    """Get all parameter values for an effect instance.

    Returns the effect instance's parameters dict directly.

    Args:
        pedalboard_id: The ID of the pedalboard.
        effect_id: The instance ID of the effect.

    Returns:
        Parameters dict keyed by name.

    Raises:
        HTTPException: 404 if pedalboard or effect instance doesn't exist.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)
    effect = get_effect_or_404(pb, effect_id)
    return effect.parameters


@router.get("/pedalboards/{pedalboard_id}/effects/{effect_id}/parameters/{param_name}")
async def get_parameter(
    pedalboard_id: int,
    effect_id: int,
    param_name: str,
    store: PedalboardStore = Depends(get_pedalboard_store)
) -> Parameter:
    """Get a specific parameter value.

    Args:
        pedalboard_id: The ID of the pedalboard.
        effect_id: The instance ID of the effect.
        param_name: The name of the parameter to retrieve.

    Returns:
        The parameter object.

    Raises:
        HTTPException: 404 if pedalboard, effect, or parameter doesn't exist.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)
    effect = get_effect_or_404(pb, effect_id)
    param = effect.parameters.get(param_name)
    if not param:
        raise HTTPException(
            status_code=404,
            detail={"error": "Parameter not found", "code": "PARAMETER_NOT_FOUND"}
        )
    return param


@router.put("/pedalboards/{pedalboard_id}/effects/{effect_id}/parameters/{param_name}", status_code=http_status.HTTP_200_OK)
async def set_parameter(
    pedalboard_id: int,
    effect_id: int,
    param_name: str,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """Set a parameter value on an effect instance.

    Sends the parameter update to mod-host and persists to pedalboard state.
    Uses patch_set for filename parameters, param_set for number parameters.

    Args:
        pedalboard_id: The ID of the pedalboard.
        effect_id: The instance ID of the effect.
        param_name: The name of the parameter to set.
        request: JSON body with 'value' field.

    Raises:
        HTTPException: 404 if pedalboard or effect instance doesn't exist.
        HTTPException: 404 if parameter doesn't exist on effect.
        HTTPException: 400 if value violates constraints or is missing.
        HTTPException: 500 if parameter update fails in mod-host.
    """
    pb = get_pedalboard_or_404(store, pedalboard_id)
    effect = get_effect_or_404(pb, effect_id)

    value = request.get("value")
    if value is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Value required", "code": "INVALID_REQUEST"}
        )

    param = effect.parameters.get(param_name)
    if not param:
        raise HTTPException(
            status_code=404,
            detail={"error": "Parameter not found", "code": "PARAMETER_NOT_FOUND"}
        )

    # Validate parameter value for number type
    if param.type == "number" and param.min is not None:
        if isinstance(value, (int, float)) and (value < param.min or value > param.max):
            raise HTTPException(
                status_code=400,
                detail={"error": "Value out of range", "code": "INVALID_PARAMETER"}
            )

    # Update mod-host based on parameter type
    if param.type == "filename":
        # Use patch_set for file parameters (like NAM model files)
        property_uri = f"{effect.uri}#{param_name}"
        param_status = client.patch_set(effect_id, property_uri, value)
    else:
        # Use param_set for numeric parameters
        param_status = client.param_set(effect_id, param_name, float(value))

    if param_status < 0:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to set parameter (code: {param_status})", "code": "PARAMETER_ERROR"}
        )

    # Update local state
    param.value = value
    store._save_pedalboard(pb)