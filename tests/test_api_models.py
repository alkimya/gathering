"""
Tests for API model schemas (Providers, Models, Personas).
Tests Pydantic validation and schema creation.
"""

import pytest
from pydantic import ValidationError

from gathering.api.routers.models import (
    ProviderBase,
    ProviderCreate,
    Provider,
    ModelBase,
    ModelCreate,
    ModelUpdate,
    Model,
    PersonaBase,
    PersonaCreate,
    PersonaUpdate,
    Persona,
)


class TestProviderSchemas:
    """Test Provider Pydantic schemas."""

    def test_provider_base_minimal(self):
        """Test creating minimal provider."""
        provider = ProviderBase(name="anthropic")
        assert provider.name == "anthropic"
        assert provider.api_base_url is None
        assert provider.is_local is False

    def test_provider_base_full(self):
        """Test creating full provider."""
        provider = ProviderBase(
            name="ollama",
            api_base_url="http://localhost:11434",
            is_local=True,
        )
        assert provider.name == "ollama"
        assert provider.api_base_url == "http://localhost:11434"
        assert provider.is_local is True

    def test_provider_create_inherits(self):
        """Test ProviderCreate inherits from ProviderBase."""
        provider = ProviderCreate(name="openai")
        assert provider.name == "openai"
        assert isinstance(provider, ProviderBase)

    def test_provider_with_id(self):
        """Test Provider schema with ID."""
        provider = Provider(
            id=1,
            name="anthropic",
            model_count=5,
        )
        assert provider.id == 1
        assert provider.name == "anthropic"
        assert provider.model_count == 5


class TestModelSchemas:
    """Test Model Pydantic schemas."""

    def test_model_base_minimal(self):
        """Test creating minimal model."""
        model = ModelBase(
            provider_id=1,
            model_name="claude-sonnet-4-20250514",
        )
        assert model.provider_id == 1
        assert model.model_name == "claude-sonnet-4-20250514"
        assert model.model_alias is None
        assert model.extended_thinking is False
        assert model.vision is False
        assert model.function_calling is True
        assert model.streaming is True

    def test_model_base_full(self):
        """Test creating full model with all fields."""
        model = ModelBase(
            provider_id=1,
            model_name="claude-sonnet-4",
            model_alias="Claude Sonnet 4",
            pricing_in=3.0,
            pricing_out=15.0,
            pricing_cache_read=0.3,
            pricing_cache_write=3.75,
            extended_thinking=True,
            vision=True,
            function_calling=True,
            streaming=True,
            context_window=200000,
            max_output=8192,
            release_date="2025-05-14",
            is_deprecated=False,
        )
        assert model.model_alias == "Claude Sonnet 4"
        assert model.pricing_in == 3.0
        assert model.pricing_out == 15.0
        assert model.extended_thinking is True
        assert model.vision is True
        assert model.context_window == 200000

    def test_model_create_inherits(self):
        """Test ModelCreate inherits from ModelBase."""
        model = ModelCreate(
            provider_id=1,
            model_name="gpt-4",
        )
        assert model.provider_id == 1
        assert isinstance(model, ModelBase)

    def test_model_update_partial(self):
        """Test ModelUpdate allows partial updates."""
        update = ModelUpdate(pricing_in=5.0)
        assert update.pricing_in == 5.0
        assert update.model_alias is None
        assert update.pricing_out is None

    def test_model_with_provider_name(self):
        """Test Model schema with provider_name."""
        model = Model(
            id=1,
            provider_id=1,
            model_name="claude-sonnet-4",
            provider_name="anthropic",
        )
        assert model.id == 1
        assert model.provider_name == "anthropic"


class TestPersonaSchemas:
    """Test Persona Pydantic schemas."""

    def test_persona_base_minimal(self):
        """Test creating minimal persona."""
        persona = PersonaBase(
            display_name="Python Expert",
            role="Senior Python Developer",
        )
        assert persona.display_name == "Python Expert"
        assert persona.role == "Senior Python Developer"
        assert persona.base_prompt is None
        assert persona.traits == []

    def test_persona_base_full(self):
        """Test creating full persona."""
        persona = PersonaBase(
            display_name="Python Expert",
            role="Senior Python Developer",
            base_prompt="You are an expert Python developer",
            full_prompt="# Python Expert\\n\\nYou are an expert...",
            traits=["analytical", "patient", "thorough"],
            specializations=["FastAPI", "pytest", "async"],
            communication_style="technical",
            languages=["English", "French"],
            motto="Code with confidence",
            description="Expert in Python development",
        )
        assert len(persona.traits) == 3
        assert "analytical" in persona.traits
        assert len(persona.specializations) == 3
        assert persona.communication_style == "technical"
        assert len(persona.languages) == 2
        assert persona.motto == "Code with confidence"

    def test_persona_create_with_model(self):
        """Test PersonaCreate with default model."""
        persona = PersonaCreate(
            display_name="Code Reviewer",
            role="Senior Code Reviewer",
            default_model_id=1,
        )
        assert persona.default_model_id == 1

    def test_persona_update_partial(self):
        """Test PersonaUpdate allows partial updates."""
        update = PersonaUpdate(
            display_name="Updated Name",
        )
        assert update.display_name == "Updated Name"
        assert update.role is None
        assert update.base_prompt is None

    def test_persona_with_id(self):
        """Test Persona schema with ID and timestamps."""
        persona = Persona(
            id=1,
            display_name="Architect",
            role="Software Architect",
            is_builtin=True,
        )
        assert persona.id == 1
        assert persona.is_builtin is True


class TestSchemaValidation:
    """Test Pydantic validation rules."""

    def test_provider_requires_name(self):
        """Test that provider name is required."""
        with pytest.raises(ValidationError):
            ProviderBase()

    def test_model_requires_provider_and_name(self):
        """Test that model requires provider_id and model_name."""
        with pytest.raises(ValidationError):
            ModelBase(provider_id=1)  # Missing model_name

        with pytest.raises(ValidationError):
            ModelBase(model_name="test")  # Missing provider_id

    def test_persona_requires_display_name_and_role(self):
        """Test that persona requires display_name and role."""
        with pytest.raises(ValidationError):
            PersonaBase(display_name="Test")  # Missing role

        with pytest.raises(ValidationError):
            PersonaBase(role="Developer")  # Missing display_name
