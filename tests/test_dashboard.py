"""
Tests for dashboard endpoints and data service.
"""

import pytest
from unittest.mock import patch, MagicMock

from gathering.api.dependencies import (
    use_demo_data,
    DataService,
    DEMO_AGENTS,
    DEMO_PROVIDERS,
    DEMO_MODELS,
)


class TestUseDemoData:
    """Test USE_DEMO_DATA toggle."""

    def test_default_is_true(self):
        """Default should be demo mode (true)."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            assert use_demo_data() is True

    def test_false_value(self):
        """Should return False when set to false."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "false"}):
            assert use_demo_data() is False

    def test_zero_value(self):
        """Should return False when set to 0."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "0"}):
            assert use_demo_data() is False

    def test_yes_value(self):
        """Should return True when set to yes."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "yes"}):
            assert use_demo_data() is True

    def test_no_value(self):
        """Should return False when set to no."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "no"}):
            assert use_demo_data() is False


class TestDataServiceDemoMode:
    """Test DataService in demo mode."""

    def test_is_demo_mode_true(self):
        """Should be in demo mode when USE_DEMO_DATA=true."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            assert data.is_demo_mode is True

    def test_get_agents_demo(self):
        """Should return demo agents."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            agents = data.get_agents()
            assert agents == DEMO_AGENTS
            assert len(agents) == 3

    def test_get_agent_demo(self):
        """Should return specific demo agent."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            agent = data.get_agent(1)
            assert agent is not None
            assert agent["name"] == "Dr. Sophie Chen"

    def test_get_agent_not_found(self):
        """Should return None for non-existent agent."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            agent = data.get_agent(999)
            assert agent is None

    def test_get_providers_demo(self):
        """Should return demo providers."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            providers = data.get_providers()
            assert providers == DEMO_PROVIDERS
            assert len(providers) == 4

    def test_get_provider_demo(self):
        """Should return specific demo provider."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            provider = data.get_provider(1)
            assert provider is not None
            assert provider["name"] == "anthropic"

    def test_get_models_demo(self):
        """Should return demo models."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            models = data.get_models()
            assert models == DEMO_MODELS
            assert len(models) == 5

    def test_get_models_filtered_demo(self):
        """Should return filtered demo models by provider."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            models = data.get_models(provider_id=1)
            assert len(models) == 2  # anthropic has 2 models in demo
            for m in models:
                assert m["provider_id"] == 1

    def test_get_model_demo(self):
        """Should return specific demo model."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "true"}):
            data = DataService(None)
            model = data.get_model(1)
            assert model is not None
            assert model["model_alias"] == "claude-sonnet-4-20250514"


class TestDataServiceDbMode:
    """Test DataService in database mode."""

    def test_is_demo_mode_false(self):
        """Should not be in demo mode when USE_DEMO_DATA=false."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "false"}):
            data = DataService(None)
            assert data.is_demo_mode is False

    def test_get_agents_db(self):
        """Should call database for agents."""
        mock_db = MagicMock()
        mock_db.get_agents.return_value = [{"id": 1, "name": "Test Agent"}]

        with patch.dict("os.environ", {"USE_DEMO_DATA": "false"}):
            data = DataService(mock_db)
            agents = data.get_agents()
            mock_db.get_agents.assert_called_once()
            assert agents == [{"id": 1, "name": "Test Agent"}]

    def test_get_agent_db(self):
        """Should call database for specific agent."""
        mock_db = MagicMock()
        mock_db.get_agent.return_value = {"id": 1, "name": "Test Agent"}

        with patch.dict("os.environ", {"USE_DEMO_DATA": "false"}):
            data = DataService(mock_db)
            agent = data.get_agent(1)
            mock_db.get_agent.assert_called_once_with(1)
            assert agent["name"] == "Test Agent"

    def test_get_providers_db(self):
        """Should call database for providers."""
        mock_db = MagicMock()
        mock_db.get_providers.return_value = [{"id": 1, "name": "test"}]

        with patch.dict("os.environ", {"USE_DEMO_DATA": "false"}):
            data = DataService(mock_db)
            providers = data.get_providers()
            mock_db.get_providers.assert_called_once()
            assert providers == [{"id": 1, "name": "test"}]

    def test_get_models_db(self):
        """Should call database for models."""
        mock_db = MagicMock()
        mock_db.get_models.return_value = [{"id": 1, "model_alias": "test"}]

        with patch.dict("os.environ", {"USE_DEMO_DATA": "false"}):
            data = DataService(mock_db)
            models = data.get_models()
            mock_db.get_models.assert_called_once_with(None)

    def test_fallback_to_demo_when_no_db(self):
        """Should fallback to demo data when DB is None in DB mode."""
        with patch.dict("os.environ", {"USE_DEMO_DATA": "false"}):
            data = DataService(None)
            agents = data.get_agents()
            # Falls back to demo data
            assert agents == DEMO_AGENTS


class TestDemoDataContent:
    """Test demo data content."""

    def test_demo_agents_structure(self):
        """Demo agents should have required fields."""
        for agent in DEMO_AGENTS:
            assert "id" in agent
            assert "name" in agent
            assert "role" in agent
            assert "provider" in agent
            assert "model" in agent
            assert "status" in agent
            assert "competencies" in agent
            assert "is_active" in agent

    def test_demo_providers_structure(self):
        """Demo providers should have required fields."""
        for provider in DEMO_PROVIDERS:
            assert "id" in provider
            assert "name" in provider
            assert "model_count" in provider

    def test_demo_models_structure(self):
        """Demo models should have required fields."""
        for model in DEMO_MODELS:
            assert "id" in model
            assert "provider_id" in model
            assert "provider_name" in model
            assert "model_alias" in model
            assert "is_deprecated" in model
