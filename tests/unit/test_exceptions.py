"""Tests for exception hierarchy and correlation ID support."""

import uuid

import pytest

from src.exceptions import (
    AgentError,
    AetherError,
    ConfigurationError,
    DALError,
    LLMError,
    MCPError,
    SandboxError,
    ValidationError,
)


class TestAetherError:
    """Test base AetherError class."""

    def test_auto_generates_correlation_id(self):
        """Test that correlation ID is auto-generated if not provided."""
        error = AetherError("Test error")
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, str)
        # Should be a valid UUID
        uuid.UUID(error.correlation_id)

    def test_accepts_custom_correlation_id(self):
        """Test that custom correlation ID can be provided."""
        custom_id = str(uuid.uuid4())
        error = AetherError("Test error", correlation_id=custom_id)
        assert error.correlation_id == custom_id

    def test_unique_correlation_ids(self):
        """Test that auto-generated correlation IDs are unique."""
        error1 = AetherError("Error 1")
        error2 = AetherError("Error 2")
        assert error1.correlation_id != error2.correlation_id

    def test_message_propagation(self):
        """Test that message is properly set."""
        error = AetherError("Test message")
        assert str(error) == "Test message"


class TestAgentError:
    """Test AgentError class."""

    def test_inherits_correlation_id(self):
        """Test that AgentError inherits correlation ID support."""
        error = AgentError("Agent failed")
        assert error.correlation_id is not None

    def test_agent_role_attribute(self):
        """Test that agent_role is stored."""
        error = AgentError("Agent failed", agent_role="architect")
        assert error.agent_role == "architect"

    def test_agent_role_optional(self):
        """Test that agent_role is optional."""
        error = AgentError("Agent failed")
        assert error.agent_role is None


class TestDALError:
    """Test DALError class."""

    def test_inherits_correlation_id(self):
        """Test that DALError inherits correlation ID support."""
        error = DALError("Database error")
        assert error.correlation_id is not None


class TestMCPError:
    """Test MCPError class."""

    def test_backward_compatibility_tool_positional(self):
        """Test backward compatibility with positional tool parameter."""
        error = MCPError("Connection failed", "connect")
        assert error.tool == "connect"
        assert error.details == {}
        assert error.correlation_id is not None

    def test_backward_compatibility_with_details(self):
        """Test backward compatibility with details parameter."""
        details = {"url": "http://localhost", "status": 500}
        error = MCPError("Connection failed", "connect", details=details)
        assert error.tool == "connect"
        assert error.details == details

    def test_status_code_attribute(self):
        """Test that status_code is stored."""
        error = MCPError("Not found", "get_entity", status_code=404)
        assert error.status_code == 404

    def test_status_code_optional(self):
        """Test that status_code is optional."""
        error = MCPError("Error", "tool")
        assert error.status_code is None

    def test_correlation_id_propagation(self):
        """Test that correlation_id can be provided."""
        custom_id = str(uuid.uuid4())
        error = MCPError("Error", "tool", correlation_id=custom_id)
        assert error.correlation_id == custom_id


class TestSandboxError:
    """Test SandboxError class."""

    def test_timeout_attribute(self):
        """Test that timeout flag is stored."""
        error = SandboxError("Script timeout", timeout=True)
        assert error.timeout is True

    def test_timeout_defaults_false(self):
        """Test that timeout defaults to False."""
        error = SandboxError("Script error")
        assert error.timeout is False


class TestLLMError:
    """Test LLMError class."""

    def test_provider_attribute(self):
        """Test that provider is stored."""
        error = LLMError("API error", provider="openai")
        assert error.provider == "openai"

    def test_provider_optional(self):
        """Test that provider is optional."""
        error = LLMError("API error")
        assert error.provider is None


class TestValidationError:
    """Test ValidationError class."""

    def test_inherits_correlation_id(self):
        """Test that ValidationError inherits correlation ID support."""
        error = ValidationError("Invalid input")
        assert error.correlation_id is not None


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_inherits_correlation_id(self):
        """Test that ConfigurationError inherits correlation ID support."""
        error = ConfigurationError("Invalid config")
        assert error.correlation_id is not None


class TestExceptionChaining:
    """Test exception chaining and correlation ID propagation."""

    def test_correlation_id_propagates_through_chain(self):
        """Test that correlation ID propagates through exception chains."""
        original_id = str(uuid.uuid4())
        original_error = MCPError("Connection failed", "connect", correlation_id=original_id)

        try:
            raise original_error
        except MCPError as e:
            # Re-raise with new context
            new_error = AgentError("Agent failed", correlation_id=e.correlation_id)
            assert new_error.correlation_id == original_id

    def test_exception_cause_preservation(self):
        """Test that exception cause is preserved."""
        original_error = MCPError("Connection failed", "connect")
        try:
            raise original_error
        except MCPError as e:
            new_error = AgentError("Agent failed", correlation_id=e.correlation_id)
            new_error.__cause__ = e
            assert new_error.__cause__ is original_error

    def test_isinstance_checks(self):
        """Test that isinstance checks work correctly."""
        error = AgentError("Test")
        assert isinstance(error, AgentError)
        assert isinstance(error, AetherError)
        assert isinstance(error, Exception)

        mcp_error = MCPError("Test", "tool")
        assert isinstance(mcp_error, MCPError)
        assert isinstance(mcp_error, AetherError)
        assert isinstance(mcp_error, Exception)


class TestErrorResponseFormat:
    """Test error response format compatibility."""

    def test_error_has_required_attributes(self):
        """Test that errors have attributes needed for API responses."""
        error = AgentError("Test error", agent_role="architect")
        assert hasattr(error, "correlation_id")
        assert error.correlation_id is not None
        assert str(error) == "Test error"

    def test_mcp_error_response_attributes(self):
        """Test that MCPError has attributes for API responses."""
        error = MCPError("Not found", "get_entity", status_code=404)
        assert hasattr(error, "correlation_id")
        assert hasattr(error, "status_code")
        assert error.status_code == 404
