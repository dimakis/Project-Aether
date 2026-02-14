"""Shared authentication helpers for API tests.

Provides make_test_settings() and make_test_jwt() used across many
unit tests that exercise authenticated API endpoints. Centralizes
the JWT secret, Settings defaults, and token generation to eliminate
duplication across 12+ test files.
"""

import time

import jwt as pyjwt
from pydantic import SecretStr

from src.settings import Settings

JWT_SECRET = "test-jwt-secret-key-for-testing-minimum-32bytes"

_SETTINGS_DEFAULTS: dict = {
    "environment": "testing",
    "debug": True,
    "database_url": "postgresql+asyncpg://test:test@localhost:5432/aether_test",
    "ha_url": "http://localhost:8123",
    "ha_token": SecretStr("test-token"),
    "openai_api_key": SecretStr("test-api-key"),
    "mlflow_tracking_uri": "http://localhost:5000",
    "sandbox_enabled": False,
    "auth_username": "admin",
    "auth_password": SecretStr("test-password"),
    "jwt_secret": SecretStr(JWT_SECRET),
    "jwt_expiry_hours": 72,
    "api_key": SecretStr(""),
}


def make_test_settings(**overrides: object) -> Settings:
    """Create test Settings with auth defaults.

    All values are safe testing defaults. Override any field via kwargs.

    Args:
        **overrides: Field overrides to merge into defaults.

    Returns:
        A Settings instance for testing.
    """
    merged = {**_SETTINGS_DEFAULTS, **overrides}
    return Settings(**merged)


def make_test_jwt(
    secret: str = JWT_SECRET,
    exp_hours: int = 72,
    sub: str = "admin",
) -> str:
    """Create a valid JWT token for testing.

    Args:
        secret: JWT signing secret.
        exp_hours: Hours until expiry.
        sub: Subject claim (username).

    Returns:
        Encoded JWT string.
    """
    payload = {
        "sub": sub,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_hours * 3600,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")
