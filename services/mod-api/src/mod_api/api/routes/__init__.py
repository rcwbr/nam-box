"""API routes package."""

from .pedalboards import router as pedalboards_router
from .effects import router as effects_router
from .connections import router as connections_router
from .ports import router as ports_router
from .parameters import router as parameters_router

__all__ = [
    "pedalboards_router",
    "effects_router",
    "connections_router",
    "ports_router",
    "parameters_router",
]