"""API route registration.

Aggregates all API routers into a single router
for inclusion in the main application.
"""

from fastapi import APIRouter

from src.api.routes.areas import router as areas_router
from src.api.routes.devices import router as devices_router
from src.api.routes.entities import router as entities_router
from src.api.routes.system import router as system_router

# Main API router
api_router = APIRouter()

# Register sub-routers
api_router.include_router(system_router, tags=["System"])
api_router.include_router(entities_router)
api_router.include_router(areas_router)
api_router.include_router(devices_router)

# Future routers:
# api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
# api_router.include_router(automations_router, prefix="/automations", tags=["Automations"])
# api_router.include_router(insights_router, prefix="/insights", tags=["Insights"])

__all__ = ["api_router"]
