"""API layer package."""

from .dependencies import get_pedalboard_store, get_effects_registry, get_mod_host_client
from .routes.pedalboards import (
    list_pedalboards,
    get_current_pedalboard,
    get_pedalboard,
    create_pedalboard,
    delete_pedalboard,
    select_pedalboard,
    rename_pedalboard,
)
from .routes.effects import (
    list_effects,
    get_effect,
    create_effect_instance,
    list_effect_instances,
    remove_effect_instance,
)
from .routes.connections import (
    create_connection,
    list_connections,
    remove_connection,
)
from .routes.ports import (
    list_ports,
)
from .routes.parameters import (
    get_parameters,
    get_parameter,
    set_parameter,
)


__all__ = [
    "get_pedalboard_store",
    "get_effects_registry",
    "get_mod_host_client",
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