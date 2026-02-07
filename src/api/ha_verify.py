"""Home Assistant token verification helper.

Validates an HA long-lived access token by calling the HA REST API.
Used during first-time setup and HA-token login.
"""

import httpx
from fastapi import HTTPException, status


async def verify_ha_connection(ha_url: str, ha_token: str) -> dict:
    """Verify a Home Assistant connection by calling GET {ha_url}/api/.

    Args:
        ha_url: The HA instance URL (e.g. "http://ha.local:8123").
        ha_token: The HA long-lived access token.

    Returns:
        The HA API response body (contains version info) on success.

    Raises:
        HTTPException: 401 if the token is invalid, 502 if HA is
            unreachable or returns an error, 504 on timeout.
    """
    # Normalize URL (strip trailing slash)
    base_url = ha_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{base_url}/api/",
                headers={"Authorization": f"Bearer {ha_token}"},
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Connection to Home Assistant at {base_url} timed out.",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot connect to Home Assistant at {base_url}. Check the URL and ensure HA is running.",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot connect to Home Assistant at {base_url}: {exc}",
        )

    if response.status_code == 200:
        return response.json()

    if response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HA token. The long-lived access token was rejected by Home Assistant.",
        )

    # Any other status code
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Home Assistant returned unexpected status {response.status_code}.",
    )
