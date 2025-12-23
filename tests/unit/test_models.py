"""
Unit tests for model schemas (LiteLLMModel, Model Union).
"""

import pytest
from pydantic import ValidationError

from interaxions.schemas import LiteLLMModel, Model


@pytest.mark.unit
class TestLiteLLMModel:
    """Tests for LiteLLMModel schema."""

    def test_litellm_model_creation_minimal(self):
        """Test creating a LiteLLM model with minimal required fields."""
        model = LiteLLMModel(
            type="litellm",
            provider="openai",
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
        )
        assert model.type == "litellm"
        assert model.provider == "openai"
        assert model.model == "gpt-4"
        assert model.base_url == "https://api.openai.com/v1"
        assert model.api_key == "sk-test-key"

    def test_litellm_model_creation_full(self):
        """Test creating a LiteLLM model with all fields."""
        model = LiteLLMModel(
            type="litellm",
            provider="openai",
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
            temperature=0.5,
            num_retries=5,
            completion_kwargs={"max_tokens": 1000},
        )
        assert model.base_url == "https://api.openai.com/v1"
        assert model.api_key == "sk-test-key"
        assert model.temperature == 0.5
        assert model.num_retries == 5
        assert model.completion_kwargs["max_tokens"] == 1000

    def test_litellm_model_required_fields(self):
        """Test that required fields must be provided."""
        with pytest.raises(ValidationError):
            LiteLLMModel(
                provider="openai",
                model="gpt-4",
                # Missing base_url and api_key
            )

    def test_litellm_model_type_must_be_litellm(self):
        """Test that type must be exactly 'litellm'."""
        with pytest.raises(ValidationError):
            LiteLLMModel(
                type="other",  # Wrong type
                provider="openai",
                model="gpt-4",
            )

    def test_litellm_model_strict_validation(self):
        """Test that extra fields are rejected (strict mode)."""
        with pytest.raises(ValidationError) as exc_info:
            LiteLLMModel(
                type="litellm",
                provider="openai",
                model="gpt-4",
                base_url="https://api.openai.com/v1",
                api_key="sk-test-key",
                extra_field="not_allowed",  # Should be rejected
            )
        assert "extra_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_litellm_model_serialization(self):
        """Test model serialization and deserialization."""
        original = LiteLLMModel(
            type="litellm",
            provider="anthropic",
            model="claude-3",
            base_url="https://api.anthropic.com/v1",
            api_key="sk-test-key",
            temperature=0.8,
        )
        
        # Serialize
        data = original.model_dump()
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-3"
        
        # Deserialize
        restored = LiteLLMModel.model_validate(data)
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.temperature == original.temperature

    def test_litellm_model_json_serialization(self):
        """Test JSON serialization."""
        model = LiteLLMModel(
            type="litellm",
            provider="openai",
            model="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
        )
        
        json_str = model.model_dump_json()
        assert "gpt-3.5-turbo" in json_str
        
        restored = LiteLLMModel.model_validate_json(json_str)
        assert restored.model == "gpt-3.5-turbo"

    def test_litellm_model_various_providers(self):
        """Test creating models with various providers."""
        # Note: only testing valid providers from Literal
        providers = ["openai", "anthropic", "litellm_proxy"]
        
        for provider in providers:
            model = LiteLLMModel(
                type="litellm",
                provider=provider,
                model=f"{provider}-model",
                base_url="https://api.example.com/v1",
                api_key="sk-test-key",
            )
            assert model.provider == provider

    def test_litellm_model_temperature_range(self):
        """Test temperature parameter with various values."""
        # Valid temperatures (0.0 to 1.0 according to Field constraint)
        for temp in [0.0, 0.5, 1.0]:
            model = LiteLLMModel(
                type="litellm",
                provider="openai",
                model="gpt-4",
                base_url="https://api.openai.com/v1",
                api_key="sk-test-key",
                temperature=temp,
            )
            assert model.temperature == temp

    def test_litellm_model_completion_kwargs(self):
        """Test completion_kwargs parameter."""
        model = LiteLLMModel(
            type="litellm",
            provider="openai",
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
            completion_kwargs={"max_tokens": 4096, "top_p": 0.9},
        )
        assert model.completion_kwargs["max_tokens"] == 4096
        assert model.completion_kwargs["top_p"] == 0.9


@pytest.mark.unit
class TestModelUnion:
    """Tests for Model Union type with discriminator."""

    def test_model_union_with_litellm(self):
        """Test that Model Union can parse LiteLLMModel."""
        from interaxions.schemas.models import Model
        
        data = {
            "type": "litellm",
            "provider": "openai",
            "model": "gpt-4",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
        }
        
        # Model Union should automatically discriminate based on "type" field
        model: Model = LiteLLMModel.model_validate(data)
        assert isinstance(model, LiteLLMModel)
        assert model.type == "litellm"

    def test_model_discriminator_validation(self):
        """Test that discriminator correctly identifies model type."""
        # With correct type field
        data_correct = {
            "type": "litellm",
            "provider": "openai",
            "model": "gpt-4",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
        }
        model = LiteLLMModel.model_validate(data_correct)
        assert model.type == "litellm"
        
        # With incorrect type field should fail
        data_incorrect = {
            "type": "unknown",
            "provider": "openai",
            "model": "gpt-4",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
        }
        with pytest.raises(ValidationError):
            LiteLLMModel.model_validate(data_incorrect)

    def test_model_union_serialization_preserves_type(self):
        """Test that serialization preserves the type field."""
        model = LiteLLMModel(
            type="litellm",
            provider="openai",
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
        )
        
        data = model.model_dump()
        assert data["type"] == "litellm"
        
        json_str = model.model_dump_json()
        assert '"type":"litellm"' in json_str or '"type": "litellm"' in json_str

