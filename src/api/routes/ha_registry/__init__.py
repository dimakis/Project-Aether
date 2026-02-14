"""HA Registry routes for automations, scripts, scenes, and services.

Provides endpoints for accessing Home Assistant registry data
including automations, scripts, scenes, and the service registry.
"""

from fastapi import APIRouter

from ._common import get_db
from .automations import router as automations_router
from .helpers import router as helpers_router
from .scenes import router as scenes_router
from .scripts import router as scripts_router
from .services import call_service
from .services import router as services_router
from .summary import router as summary_router
from .sync import RegistrySyncResponse, sync_registry
from .sync import router as sync_router

router = APIRouter(tags=["HA Registry"])

router.include_router(sync_router)
router.include_router(automations_router)
router.include_router(scripts_router)
router.include_router(scenes_router)
router.include_router(services_router)
router.include_router(helpers_router)
router.include_router(summary_router)

__all__ = [
    "RegistrySyncResponse",
    "call_service",
    "get_db",
    "router",
    "sync_registry",
]
