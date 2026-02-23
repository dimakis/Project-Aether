"""Tests for WorkflowDefinitionEntity DB model (Feature 29).

Covers:
- Entity has required columns for persisting workflow configs
- Status lifecycle (draft, active, archived)
- JSONB storage for nodes, edges, conditional_edges
- Intent patterns for auto-routing
"""

from __future__ import annotations


class TestWorkflowDefinitionEntity:
    """WorkflowDefinitionEntity stores declarative workflow configs in Postgres."""

    def test_entity_has_name_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.name
        assert col is not None
        assert not col.nullable

    def test_entity_has_description_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.description
        assert col is not None

    def test_entity_has_state_type_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.state_type
        assert col is not None
        assert not col.nullable

    def test_entity_has_config_jsonb_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.config
        assert col is not None

    def test_entity_has_status_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.status
        assert col is not None
        assert str(col.server_default.arg) == "draft"

    def test_entity_has_version_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.version
        assert col is not None

    def test_entity_has_intent_patterns_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.intent_patterns
        assert col is not None

    def test_entity_has_created_by_column(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        col = WorkflowDefinitionEntity.__table__.c.created_by
        assert col is not None

    def test_entity_can_be_instantiated(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        entity = WorkflowDefinitionEntity(
            name="test-workflow",
            description="A test",
            state_type="ConversationState",
            config={"nodes": [], "edges": []},
        )
        assert entity.name == "test-workflow"
        assert entity.config == {"nodes": [], "edges": []}

    def test_tablename(self):
        from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

        assert WorkflowDefinitionEntity.__tablename__ == "workflow_definition"
