"""mod-api module for pedalboard management."""

from .api import (
    list_pedalboards,
    get_current_pedalboard,
    get_pedalboard,
    create_pedalboard,
    delete_pedalboard,
    select_pedalboard,
    rename_pedalboard,
    list_effects,
    get_effect,
    create_effect_instance,
    list_effect_instances,
    remove_effect_instance,
    create_connection,
    list_connections,
    remove_connection,
    list_ports,
    get_parameters,
    get_parameter,
    set_parameter,
)

__all__ = [
    "list_pedalboards",
    "get_current_pedalboard",
    "get_pedalboard",
    "create_pedalboard",
    "delete_pedalboard",
    "select_pedalboard",
    "rename_pedalboard",
    "list_effects",
    "get_effect",
    "create_effect_instance",
    "list_effect_instances",
    "remove_effect_instance",
    "create_connection",
    "list_connections",
    "remove_connection",
    "list_ports",
    "get_parameters",
    "get_parameter",
    "set_parameter",
]


# Models, storage, and effects are available via separate imports for tests:
# from models import Parameter, ParameterInfo, EffectInfo
# from models import Pedalboard, EffectInstance, Connection, Port
# from utils.mod_host_client import ModHostClient
# from storage.pedalboard_store import PedalboardStore
# from effects.registry import EffectsRegistry