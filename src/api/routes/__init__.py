"""API route registration.

Aggregates all API routers into a single router
for inclusion in the main application.
"""

from fastapi import APIRouter

from src.api.routes.activity_stream import router as activity_router
from src.api.routes.agents import router as agents_router
from src.api.routes.areas import router as areas_router
from src.api.routes.artifacts import router as artifacts_router
from src.api.routes.auth import router as auth_router
from src.api.routes.chat import router as chat_router
from src.api.routes.devices import router as devices_router
from src.api.routes.diagnostics import router as diagnostics_router
from src.api.routes.entities import router as entities_router
from src.api.routes.evaluations import router as evaluations_router
from src.api.routes.flow_grades import router as flow_grades_router
from src.api.routes.ha_registry import router as ha_registry_router
from src.api.routes.ha_zones import router as ha_zones_router
from src.api.routes.insight_schedules import router as insight_schedules_router
from src.api.routes.insights import router as insights_router
from src.api.routes.model_ratings import router as model_ratings_router
from src.api.routes.openai_compat import router as openai_router
from src.api.routes.optimization import router as optimization_router
from src.api.routes.passkey import router as passkey_router
from src.api.routes.proposals import router as proposals_router
from src.api.routes.system import router as system_router
from src.api.routes.traces import router as traces_router
from src.api.routes.usage import router as usage_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.workflows import router as workflows_router

# Main API router
api_router = APIRouter()

# Authentication
api_router.include_router(auth_router)
api_router.include_router(passkey_router)
# System
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
# Feature 03: Intelligent Optimization
api_router.include_router(optimization_router)
# Feature 10: Scheduled & Event-Driven Insights
api_router.include_router(insight_schedules_router)
api_router.include_router(webhooks_router)
# Feature 11: Agent Activity Trace
api_router.include_router(traces_router)
# LLM Usage Tracking
api_router.include_router(usage_router)
# Feature 23: Agent Configuration
api_router.include_router(agents_router)
# Model Registry - per-agent model ratings
api_router.include_router(model_ratings_router)
# Diagnostics - HA health, error logs, config check, traces
api_router.include_router(diagnostics_router)
# Workflow presets
api_router.include_router(workflows_router)
# OpenAI-compatible API for Open WebUI
api_router.include_router(openai_router)
# Global activity stream
api_router.include_router(activity_router)
# Flow grading
api_router.include_router(flow_grades_router)
# Trace evaluation (MLflow 3.x GenAI scorers)
api_router.include_router(evaluations_router)
# HA Zones (multi-server)
api_router.include_router(ha_zones_router)
# Feature 33: DS Deep Analysis — Artifact serving
api_router.include_router(artifacts_router)
# Feature 33: DS Deep Analysis — Analysis Reports
from src.api.routes.reports import router as reports_router

api_router.include_router(reports_router)

__all__ = ["api_router"]
