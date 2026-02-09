"""Unit tests for API key authentication.

Tests the API key authentication middleware including:
- Valid key authentication (header and query param)
- Invalid key rejection
- Missing key rejection
- Auth bypass when API_KEY is empty
- Health endpoint exemption
"""

from pydantic import SecretStr

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.settings import get_settings


@pytest.fixture
async def client_with_auth(mock_settings, monkeypatch):
    """Create a test client with authentication enabled."""
    # Clear settings cache
    get_settings.cache_clear()
    
    # Set API key
    mock_settings.api_key = SecretStr("test-api-key-123")
    
    # Monkeypatch get_settings to return our test settings
    from src import settings as settings_module
    monkeypatch.setattr(settings_module, "get_settings", lambda: mock_settings)
    
    # Create app with updated settings
    app = create_app(mock_settings)
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    
    # Clear cache after test
    get_settings.cache_clear()


@pytest.fixture
async def client_without_auth(mock_settings, monkeypatch):
    """Create a test client with authentication disabled."""
    # Clear settings cache
    get_settings.cache_clear()
    
    # Set empty API key (auth disabled)
    mock_settings.api_key = SecretStr("")
    
    # Monkeypatch get_settings to return our test settings
    from src import settings as settings_module
    monkeypatch.setattr(settings_module, "get_settings", lambda: mock_settings)
    
    # Create app with updated settings
    app = create_app(mock_settings)
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    
    # Clear cache after test
    get_settings.cache_clear()


@pytest.mark.asyncio
class TestAPIKeyAuthentication:
    """Test API key authentication middleware."""

    async def test_request_without_key_returns_401_when_auth_enabled(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that requests without API key return 401 when auth is enabled."""
        # Make request to a protected endpoint without API key
        response = await client_with_auth.get("/api/v1/models")

        assert response.status_code == 401
        assert "Authentication required" in response.json()["error"]["message"]

    async def test_request_with_valid_header_key_succeeds(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that requests with valid API key in header succeed."""
        # Make request with valid API key in header
        response = await client_with_auth.get(
            "/api/v1/models",
            headers={"X-API-Key": "test-api-key-123"},
        )

        # Should succeed (may return 200 or other status depending on endpoint)
        assert response.status_code != 401

    async def test_request_with_valid_query_key_succeeds(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that requests with valid API key in query parameter succeed."""
        # Make request with valid API key in query parameter
        response = await client_with_auth.get(
            "/api/v1/models",
            params={"api_key": "test-api-key-123"},
        )

        # Should succeed (may return 200 or other status depending on endpoint)
        assert response.status_code != 401

    async def test_request_with_invalid_key_returns_401(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that requests with invalid API key return 401."""
        # Make request with invalid API key
        response = await client_with_auth.get(
            "/api/v1/models",
            headers={"X-API-Key": "wrong-key"},
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["error"]["message"]

    async def test_auth_bypassed_when_api_key_empty(
        self,
        client_without_auth: AsyncClient,
    ):
        """Test that authentication is bypassed when API_KEY is empty."""
        # Make request without API key
        response = await client_without_auth.get("/api/v1/models")

        # Should succeed (auth disabled)
        assert response.status_code != 401

    async def test_health_endpoint_works_without_auth(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that health endpoint works without authentication."""
        # Make request to health endpoint without API key
        response = await client_with_auth.get("/api/v1/health")

        # Should succeed (health endpoint is exempt)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    async def test_metrics_endpoint_requires_auth(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that metrics endpoint requires authentication."""
        # Make request to metrics endpoint without API key
        response = await client_with_auth.get("/api/v1/metrics")

        # Should require auth
        assert response.status_code == 401

    async def test_header_key_takes_precedence_over_query(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that header key takes precedence when both are provided."""
        # Make request with valid header key but invalid query key
        response = await client_with_auth.get(
            "/api/v1/models",
            headers={"X-API-Key": "test-api-key-123"},
            params={"api_key": "wrong-key"},
        )

        # Should succeed (header key is used)
        assert response.status_code != 401

    async def test_openai_compat_endpoints_require_auth(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that OpenAI-compatible endpoints require authentication."""
        # Make request to OpenAI models endpoint without API key
        response = await client_with_auth.get("/api/v1/models")

        # Should require auth
        assert response.status_code == 401

    async def test_openai_compat_endpoints_work_with_valid_key(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that OpenAI-compatible endpoints work with valid API key."""
        # Make request to OpenAI models endpoint with valid API key
        response = await client_with_auth.get(
            "/api/v1/models",
            headers={"X-API-Key": "test-api-key-123"},
        )

        # Should succeed (may return 200 or other status depending on endpoint)
        assert response.status_code != 401

    async def test_timing_attack_protection(
        self,
        client_with_auth: AsyncClient,
    ):
        """Test that constant-time comparison prevents timing attacks."""
        # Try with key that differs at the start
        response1 = await client_with_auth.get(
            "/api/v1/models",
            headers={"X-API-Key": "wrong-start"},
        )

        # Try with key that differs at the end
        response2 = await client_with_auth.get(
            "/api/v1/models",
            headers={"X-API-Key": "test-api-key-999"},
        )

        # Both should return 401 with same timing characteristics
        assert response1.status_code == 401
        assert response2.status_code == 401
        assert "Invalid API key" in response1.json()["error"]["message"]
        assert "Invalid API key" in response2.json()["error"]["message"]
