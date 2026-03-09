"""Energy tariff API endpoints.

Provides tariff configuration data for the /energy UI page
and the dashboard summary card.

Feature 40: Electricity Tariff Management.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from src.api.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/energy", tags=["Energy"])


@router.get("/tariffs")
@limiter.limit("30/minute")
async def get_tariffs(request: Request) -> dict[str, Any]:
    """Return current electricity tariff configuration.

    Reads the tariff input_number/text/select entities from HA.
    Returns configured=False if tariff helpers have not been set up.
    """
    from src.ha import get_ha_client_async
    from src.tools.tariff_tools import get_tariff_rates

    try:
        ha = await get_ha_client_async()
        return await get_tariff_rates(ha)
    except Exception:
        logger.exception("Failed to read tariff rates from HA")
        return {"configured": False}
