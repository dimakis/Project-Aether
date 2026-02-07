"""ORM relationship tests.

Validates the ORM relationship fixes from the production readiness sprint:
- Agent has active_config_version and active_prompt_version relationships
- LLMUsage has conversation FK and relationship
- Eager loading (selectin) prevents N+1 queries
"""

import pytest
from unittest.mock import patch, AsyncMock


# =============================================================================
# AGENT MODEL RELATIONSHIPS
# =============================================================================


class TestAgentRelationships:
    """Test Agent model has correct relationships defined."""

    def test_agent_has_active_config_version_relationship(self):
        """Agent should have active_config_version relationship."""
        from src.storage.entities.agent import Agent

        mapper = Agent.__mapper__
        relationships = {r.key for r in mapper.relationships}
        assert "active_config_version" in relationships

    def test_agent_has_active_prompt_version_relationship(self):
        """Agent should have active_prompt_version relationship."""
        from src.storage.entities.agent import Agent

        mapper = Agent.__mapper__
        relationships = {r.key for r in mapper.relationships}
        assert "active_prompt_version" in relationships

    def test_agent_has_conversations_relationship(self):
        """Agent should have conversations relationship."""
        from src.storage.entities.agent import Agent

        mapper = Agent.__mapper__
        relationships = {r.key for r in mapper.relationships}
        assert "conversations" in relationships

    def test_agent_has_config_versions_relationship(self):
        """Agent should have config_versions collection relationship."""
        from src.storage.entities.agent import Agent

        mapper = Agent.__mapper__
        relationships = {r.key for r in mapper.relationships}
        assert "config_versions" in relationships

    def test_agent_has_prompt_versions_relationship(self):
        """Agent should have prompt_versions collection relationship."""
        from src.storage.entities.agent import Agent

        mapper = Agent.__mapper__
        relationships = {r.key for r in mapper.relationships}
        assert "prompt_versions" in relationships

    def test_active_config_version_uses_post_update(self):
        """active_config_version should use post_update to break circular dependency."""
        from src.storage.entities.agent import Agent

        for rel in Agent.__mapper__.relationships:
            if rel.key == "active_config_version":
                assert rel.post_update is True
                break
        else:
            pytest.fail("active_config_version relationship not found")

    def test_active_prompt_version_uses_post_update(self):
        """active_prompt_version should use post_update to break circular dependency."""
        from src.storage.entities.agent import Agent

        for rel in Agent.__mapper__.relationships:
            if rel.key == "active_prompt_version":
                assert rel.post_update is True
                break
        else:
            pytest.fail("active_prompt_version relationship not found")


# =============================================================================
# LLM USAGE MODEL RELATIONSHIPS
# =============================================================================


class TestLLMUsageRelationships:
    """Test LLMUsage model has correct relationships defined."""

    def test_llm_usage_has_conversation_relationship(self):
        """LLMUsage should have conversation relationship."""
        from src.storage.entities.llm_usage import LLMUsage

        mapper = LLMUsage.__mapper__
        relationships = {r.key for r in mapper.relationships}
        assert "conversation" in relationships

    def test_llm_usage_conversation_id_has_fk(self):
        """LLMUsage.conversation_id should have a FK to conversation.id."""
        from src.storage.entities.llm_usage import LLMUsage

        col = LLMUsage.__table__.c.conversation_id
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert "conversation.id" in str(fks[0].target_fullname)

    def test_llm_usage_has_conversation_id_index(self):
        """LLMUsage should have an index on conversation_id."""
        from src.storage.entities.llm_usage import LLMUsage

        index_names = {idx.name for idx in LLMUsage.__table__.indexes}
        assert "ix_llm_usage_conversation_id" in index_names


# =============================================================================
# EAGER LOADING VERIFICATION
# =============================================================================


class TestEagerLoading:
    """Test that relationships use selectin loading for async compatibility."""

    def test_agent_relationships_use_selectin(self):
        """All Agent relationships should use selectin lazy loading."""
        from src.storage.entities.agent import Agent

        for rel in Agent.__mapper__.relationships:
            assert rel.lazy == "selectin", (
                f"Agent.{rel.key} uses lazy={rel.lazy!r}, expected 'selectin'"
            )

    def test_llm_usage_conversation_uses_selectin(self):
        """LLMUsage.conversation should use selectin lazy loading."""
        from src.storage.entities.llm_usage import LLMUsage

        for rel in LLMUsage.__mapper__.relationships:
            if rel.key == "conversation":
                assert rel.lazy == "selectin"
                break
        else:
            pytest.fail("conversation relationship not found")
