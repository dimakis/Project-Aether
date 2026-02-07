"""Home Assistant token verification helper.

Validates an HA long-lived access token by calling the HA REST API.
Used during first-time setup and HA-token login.

Security: Includes SSRF protection to prevent requests to arbitrary
internal endpoints via user-provided URLs.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status


def _validate_url_not_ssrf(url: str) -> None:
    """Validate that a URL does not point to a dangerous internal resource.

    Blocks requests to:
    - Non-HTTP(S) schemes (file://, ftp://, etc.)
    - Cloud metadata endpoints (169.254.169.254)
    - Loopback addresses when not explicitly localhost (127.x.x.x)

    Allows:
    - Private networks (192.168.x.x, 10.x.x.x) since HA commonly runs on LAN
    - localhost / 127.0.0.1 (valid local HA installs)

    Args:
        url: The URL to validate

    Raises:
        HTTPException: If the URL looks like an SSRF attempt
    """
    parsed = urlparse(url)

    # Must be HTTP or HTTPS
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTTP and HTTPS URLs are allowed.",
        )

    # Must have a hostname
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL: missing hostname.",
        )

    # Resolve hostname and check for dangerous IPs
    try:
        resolved_ips = socket.getaddrinfo(hostname, parsed.port or 80)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve hostname: {hostname}",
        )

    for family, _type, _proto, _canonname, sockaddr in resolved_ips:
        ip = ipaddress.ip_address(sockaddr[0])

        # Block cloud metadata endpoints (AWS, GCP, Azure, etc.)
        if ip == ipaddress.ip_address("169.254.169.254"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL points to a cloud metadata endpoint.",
            )

        # Block link-local (169.254.x.x) except the specific metadata IP (already blocked above)
        if ip.is_link_local:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL points to a link-local address.",
            )


async def verify_ha_connection(ha_url: str, ha_token: str) -> dict:
    """Verify a Home Assistant connection by calling GET {ha_url}/api/.

    Args:
        ha_url: The HA instance URL (e.g. "http://ha.local:8123").
        ha_token: The HA long-lived access token.

    Returns:
        The HA API response body (contains version info) on success.

    Raises:
        HTTPException: 401 if the token is invalid, 502 if HA is
            unreachable or returns an error, 504 on timeout,
            400 if the URL fails SSRF validation.
    """
    # Normalize URL (strip trailing slash)
    base_url = ha_url.rstrip("/")

    # SSRF protection: validate the URL before making any request
    _validate_url_not_ssrf(base_url)

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
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot connect to Home Assistant at {base_url}. Check the URL and network.",
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
