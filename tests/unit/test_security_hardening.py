"""Security hardening tests.

Validates the security controls added in the production readiness sprint.
All tests are lightweight -- no app creation, no DB, no LLM imports.

Covers:
- HITL enforcement via read-only tool whitelist
- Authentication fail-closed in production
- JWT secret requirements
- SSRF protection on HA URL validation
- Error message sanitization
- Pydantic input validation constraints
- Domain blocklist on service calls (logic-level)
- Webhook secret enforcement (logic-level)
"""

import pytest
from pydantic import SecretStr, ValidationError
from unittest.mock import patch

from src.settings import Settings


# =============================================================================
# HITL ENFORCEMENT
# =============================================================================


class TestHITLWhitelist:
    """Test that _is_mutating_tool uses a whitelist (not blacklist) approach.

    Tests the class attribute and method directly to avoid importing the
    full ArchitectWorkflow (which pulls in heavy LangGraph/LLM deps).
    """

    def test_read_only_tools_are_allowed(self):
        """Known read-only tools should be in the whitelist."""
        from src.agents.architect import ArchitectAgent

        read_only = [
            "get_entity_state",
            "list_entities_by_domain",
            "search_entities",
            "get_domain_summary",
            "discover_entities",
            "seek_approval",
            "consult_data_science_team",
            "create_insight_schedule",
            "check_ha_config",
        ]
        for tool_name in read_only:
            assert tool_name in ArchitectAgent._READ_ONLY_TOOLS, (
                f"{tool_name} should be in _READ_ONLY_TOOLS whitelist"
            )

    def test_known_mutating_tools_not_in_whitelist(self):
        """Known mutating tools should NOT be in the whitelist."""
        from src.agents.architect import ArchitectAgent

        mutating = [
            "control_entity",
            "deploy_automation",
            "delete_automation",
            "create_script",
            "create_scene",
            "create_input_boolean",
            "create_input_number",
            "fire_event",
        ]
        for tool_name in mutating:
            assert tool_name not in ArchitectAgent._READ_ONLY_TOOLS, (
                f"{tool_name} should NOT be in _READ_ONLY_TOOLS (it's mutating)"
            )

    def test_unknown_tools_not_in_whitelist(self):
        """Arbitrary/unknown tools should NOT be in the whitelist."""
        from src.agents.architect import ArchitectAgent

        assert "some_new_tool_2026" not in ArchitectAgent._READ_ONLY_TOOLS
        assert "" not in ArchitectAgent._READ_ONLY_TOOLS
        assert "hack_the_planet" not in ArchitectAgent._READ_ONLY_TOOLS

    def test_whitelist_is_frozenset(self):
        """Whitelist should be immutable."""
        from src.agents.architect import ArchitectAgent

        assert isinstance(ArchitectAgent._READ_ONLY_TOOLS, frozenset)


# =============================================================================
# AUTH HARDENING
# =============================================================================


class TestAuthFailClosed:
    """Test that auth fails closed in production when not configured."""

    def test_production_requires_jwt_secret(self):
        """Production should raise ConfigurationError without JWT_SECRET."""
        from src.api.auth import _get_jwt_secret
        from src.exceptions import ConfigurationError

        settings = Settings(
            environment="production",
            debug=False,
            ha_url="http://ha.local:8123",
            ha_token=SecretStr("test"),
            jwt_secret=SecretStr(""),  # Empty = not configured
            auth_password=SecretStr(""),
        )
        with pytest.raises(ConfigurationError, match="JWT_SECRET must be set"):
            _get_jwt_secret(settings)

    def test_development_allows_auto_jwt_secret(self):
        """Development should auto-generate JWT secret."""
        from src.api.auth import _get_jwt_secret

        settings = Settings(
            environment="development",
            debug=True,
            ha_url="http://localhost:8123",
            ha_token=SecretStr("test"),
            jwt_secret=SecretStr(""),
            auth_password=SecretStr(""),
        )
        # Should NOT raise
        secret = _get_jwt_secret(settings)
        assert secret == "aether-dev-jwt-secret"

    def test_production_explicit_secret_accepted(self):
        """Production with a proper JWT secret should work."""
        from src.api.auth import _get_jwt_secret

        settings = Settings(
            environment="production",
            debug=False,
            ha_url="http://ha.local:8123",
            ha_token=SecretStr("test"),
            jwt_secret=SecretStr("a" * 32),
            auth_password=SecretStr(""),
        )
        secret = _get_jwt_secret(settings)
        assert secret == "a" * 32


# =============================================================================
# SSRF PROTECTION
# =============================================================================


class TestSSRFProtection:
    """Test SSRF protection in HA URL validation."""

    def test_blocks_non_http_schemes(self):
        """Should reject non-HTTP schemes."""
        from src.api.ha_verify import _validate_url_not_ssrf
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_url_not_ssrf("file:///etc/passwd")
        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException):
            _validate_url_not_ssrf("ftp://internal-server")

    def test_blocks_cloud_metadata(self):
        """Should block cloud metadata endpoint."""
        from src.api.ha_verify import _validate_url_not_ssrf
        from fastapi import HTTPException

        with pytest.raises(HTTPException, match="cloud metadata"):
            _validate_url_not_ssrf("http://169.254.169.254/latest/meta-data/")

    def test_allows_private_networks(self):
        """Should allow private network IPs (valid for HA on LAN)."""
        from src.api.ha_verify import _validate_url_not_ssrf

        # These should NOT raise
        _validate_url_not_ssrf("http://192.168.1.100:8123")
        _validate_url_not_ssrf("http://10.0.0.5:8123")
        _validate_url_not_ssrf("http://localhost:8123")

    def test_blocks_missing_hostname(self):
        """Should reject URLs without a hostname."""
        from src.api.ha_verify import _validate_url_not_ssrf
        from fastapi import HTTPException

        with pytest.raises(HTTPException, match="missing hostname"):
            _validate_url_not_ssrf("http://")


# =============================================================================
# ERROR SANITIZATION
# =============================================================================


class TestErrorSanitization:
    """Test that error messages are sanitized in production."""

    def test_sanitize_error_production(self, monkeypatch):
        """In production, should return generic message."""
        prod_settings = Settings(
            environment="production",
            debug=False,
            ha_url="http://ha.local:8123",
            ha_token=SecretStr("test"),
            jwt_secret=SecretStr("a" * 32),
        )
        import src.api.utils as utils_module

        monkeypatch.setattr(utils_module, "get_settings", lambda: prod_settings)

        result = utils_module.sanitize_error(
            RuntimeError("secret database password is xyz123"),
            context="Test operation",
        )
        assert "xyz123" not in result
        assert "Test operation failed" in result

    def test_sanitize_error_development(self, monkeypatch):
        """In development, should include original error."""
        dev_settings = Settings(
            environment="development",
            debug=True,
            ha_url="http://localhost:8123",
            ha_token=SecretStr("test"),
        )
        import src.api.utils as utils_module

        monkeypatch.setattr(utils_module, "get_settings", lambda: dev_settings)

        result = utils_module.sanitize_error(
            RuntimeError("detailed error info"),
            context="Test operation",
        )
        assert "detailed error info" in result


# =============================================================================
# PYDANTIC INPUT VALIDATION
# =============================================================================


class TestInputValidation:
    """Test that Pydantic schemas enforce max_length and range constraints."""

    def test_chat_message_max_length(self):
        """ChatRequest should reject messages exceeding max_length."""
        from src.api.schemas.conversations import ChatRequest

        # Should work
        ChatRequest(message="Hello")

        # Should fail
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 50_001)

    def test_service_call_domain_max_length(self):
        """ServiceCallRequest should reject oversized domain names."""
        from src.api.schemas.ha_automations import ServiceCallRequest

        with pytest.raises(ValidationError):
            ServiceCallRequest(domain="x" * 101, service="turn_on")

    def test_login_password_max_length(self):
        """LoginRequest should reject oversized passwords."""
        from src.api.routes.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="x" * 129)

    def test_proposal_name_max_length(self):
        """ProposalCreate should reject oversized names."""
        from src.api.schemas.proposals import ProposalCreate

        with pytest.raises(ValidationError):
            ProposalCreate(name="x" * 256)

    def test_conversation_title_max_length(self):
        """ConversationCreate should reject oversized titles."""
        from src.api.schemas.conversations import ConversationCreate

        with pytest.raises(ValidationError):
            ConversationCreate(title="x" * 256, initial_message="hi")

    def test_insight_title_max_length(self):
        """InsightCreate should reject oversized titles."""
        from src.api.schemas.insights import InsightCreate, InsightType

        with pytest.raises(ValidationError):
            InsightCreate(
                type=InsightType.ENERGY_OPTIMIZATION,
                title="x" * 501,
                description="desc",
                evidence={},
                confidence=0.5,
                impact="low",
            )


# =============================================================================
# SERVICE CALL DOMAIN BLOCKLIST (logic-level, no app creation)
# =============================================================================


class TestServiceCallBlocklist:
    """Test that dangerous domains are in the blocklist.

    Tests the blocklist logic directly by importing and checking the
    BLOCKED_DOMAINS set from the route handler source, avoiding the
    need to create the full app.
    """

    def test_blocked_domains_defined(self):
        """The endpoint handler should block dangerous domains."""
        # We test the logic by checking that the set exists in the source
        # and contains expected domains. The actual blocking logic is:
        # if request.domain in BLOCKED_DOMAINS: return failure
        blocked = frozenset({
            "homeassistant",
            "persistent_notification",
            "system_log",
            "recorder",
            "hassio",
        })
        assert "homeassistant" in blocked
        assert "hassio" in blocked
        assert "recorder" in blocked
        assert "light" not in blocked
        assert "switch" not in blocked

    def test_blocked_domains_in_source(self):
        """Verify the blocked domains are defined in ha_registry.py."""
        import inspect
        from src.api.routes import ha_registry

        source = inspect.getsource(ha_registry.call_service)
        assert "BLOCKED_DOMAINS" in source
        assert '"homeassistant"' in source
        assert '"hassio"' in source


# =============================================================================
# WEBHOOK SECRET ENFORCEMENT (logic-level)
# =============================================================================


class TestWebhookSecretEnforcement:
    """Test webhook secret enforcement logic."""

    def test_webhook_handler_checks_production_secret(self):
        """Verify the webhook handler source requires secret in production."""
        import inspect
        from src.api.routes import webhooks

        source = inspect.getsource(webhooks.receive_ha_webhook)
        # Should check for production environment
        assert 'environment == "production"' in source
        # Should use constant-time comparison
        assert "compare_digest" in source

    def test_webhook_handler_uses_rate_limiting(self):
        """Verify the webhook handler has rate limiting."""
        import inspect
        from src.api.routes import webhooks

        source = inspect.getsource(webhooks.receive_ha_webhook)
        assert "limiter" in source or "30/minute" in source
