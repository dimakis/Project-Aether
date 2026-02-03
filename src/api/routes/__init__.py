"""API route registration.

Aggregates all API routers into a single router
for inclusion in the main application.
"""

from fastapi import APIRouter

from src.api.routes.system import router as system_router

# Main API router
api_router = APIRouter()

# Register sub-routers
api_router.include_router(system_router, tags=["System"])

# Future routers will be added here:
# api_router.include_router(discovery_router, prefix="/discovery", tags=["Discovery"])
# api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
# api_router.include_router(automations_router, prefix="/automations", tags=["Automations"])
# api_router.include_router(insights_router, prefix="/insights", tags=["Insights"])

__all__ = ["api_router"]
