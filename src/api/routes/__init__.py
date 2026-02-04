"""API route registration.

Aggregates all API routers into a single router
for inclusion in the main application.
"""

from fastapi import APIRouter

from src.api.routes.areas import router as areas_router
from src.api.routes.chat import router as chat_router
from src.api.routes.devices import router as devices_router
from src.api.routes.entities import router as entities_router
from src.api.routes.ha_registry import router as ha_registry_router
from src.api.routes.insights import router as insights_router
from src.api.routes.proposals import router as proposals_router
from src.api.routes.system import router as system_router

# Main API router
api_router = APIRouter()

# Register sub-routers
api_router.include_router(system_router, tags=["System"])
api_router.include_router(entities_router)
api_router.include_router(areas_router)
api_router.include_router(devices_router)
api_router.include_router(ha_registry_router, prefix="/registry")
# User Story 2: Conversations and Proposals
api_router.include_router(chat_router)
api_router.include_router(proposals_router)
# User Story 3: Insights and Analysis
api_router.include_router(insights_router)

__all__ = ["api_router"]
