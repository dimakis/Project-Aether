"""Unit tests for model rating entity.

TDD: Test for Plan 7 - Model Registry.
"""


class TestModelRatingEntity:
    """Test ModelRating model."""

    def test_create_model_rating(self):
        """Test creating a ModelRating instance."""
        from src.storage.entities.model_rating import ModelRating

        rating = ModelRating(
            id="test-uuid",
            model_name="gpt-4o",
            agent_role="architect",
            rating=4,
            notes="Good at generating automations",
            config_snapshot={"temperature": 0.7, "context_window": 128000},
        )

        assert rating.model_name == "gpt-4o"
        assert rating.agent_role == "architect"
        assert rating.rating == 4
        assert rating.notes == "Good at generating automations"
        assert rating.config_snapshot["temperature"] == 0.7

    def test_model_rating_repr(self):
        """Test ModelRating repr."""
        from src.storage.entities.model_rating import ModelRating

        rating = ModelRating(
            id="test-uuid",
            model_name="gemini-2.5-flash",
            agent_role="data_scientist",
            rating=5,
        )

        assert "gemini-2.5-flash" in repr(rating)
        assert "data_scientist" in repr(rating)
        assert "5" in repr(rating)
