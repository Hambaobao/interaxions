"""
Unit tests for model schemas (OpenAIModel, AnthropicModel, LiteLLMModel, Model Union).
"""

import pytest
from pydantic import ValidationError

from interaxions.schemas import LiteLLMModel
from interaxions.schemas.models import AnthropicModel, Model, OpenAIModel


# ============================================================================
# OpenAIModel
# ============================================================================


@pytest.mark.unit
class TestOpenAIModel:
    """Tests for OpenAIModel schema."""

    def test_minimal_creation(self):
        model = OpenAIModel(model="gpt-4o", api_key="sk-test")
        assert model.type == "openai"
        assert model.model == "gpt-4o"
        assert model.api_key == "sk-test"
        assert model.base_url == "https://api.openai.com/v1"

    def test_full_creation(self):
        model = OpenAIModel(
            model="gpt-4o",
            api_key="sk-test",
            base_url="https://custom.openai.com/v1",
            num_retries=5,
            temperature=0.5,
            max_tokens=2048,
            completion_kwargs={"top_p": 0.9},
        )
        assert model.base_url == "https://custom.openai.com/v1"
        assert model.num_retries == 5
        assert model.temperature == 0.5
        assert model.max_tokens == 2048
        assert model.completion_kwargs["top_p"] == 0.9

    def test_type_is_always_openai(self):
        model = OpenAIModel(model="gpt-4o", api_key="sk-test")
        assert model.type == "openai"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            OpenAIModel(api_key="sk-test")  # missing model

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            OpenAIModel(model="gpt-4o", api_key="sk-test", unknown_field="value")

    def test_serialization_roundtrip(self):
        original = OpenAIModel(model="gpt-4o", api_key="sk-test", temperature=0.7)
        restored = OpenAIModel.model_validate(original.model_dump())
        assert restored.model == original.model
        assert restored.temperature == original.temperature


# ============================================================================
# AnthropicModel
# ============================================================================


@pytest.mark.unit
class TestAnthropicModel:
    """Tests for AnthropicModel schema."""

    def test_minimal_creation(self):
        model = AnthropicModel(model="claude-3-5-sonnet-latest", api_key="sk-ant-test")
        assert model.type == "anthropic"
        assert model.model == "claude-3-5-sonnet-latest"
        assert model.api_key == "sk-ant-test"
        assert model.base_url == "https://api.anthropic.com"

    def test_temperature_range(self):
        # Valid range for Anthropic: 0.0 – 1.0
        for temp in [0.0, 0.5, 1.0]:
            model = AnthropicModel(model="claude-3-5-sonnet-latest", api_key="sk-test", temperature=temp)
            assert model.temperature == temp

    def test_temperature_out_of_range(self):
        with pytest.raises(ValidationError):
            AnthropicModel(model="claude-3-5-sonnet-latest", api_key="sk-test", temperature=1.5)

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            AnthropicModel(model="claude-3-5-sonnet-latest", api_key="sk-test", extra="not allowed")

    def test_serialization_roundtrip(self):
        original = AnthropicModel(model="claude-3-5-sonnet-latest", api_key="sk-test")
        restored = AnthropicModel.model_validate(original.model_dump())
        assert restored.model == original.model
        assert restored.type == "anthropic"


# ============================================================================
# LiteLLMModel
# ============================================================================


@pytest.mark.unit
class TestLiteLLMModel:
    """Tests for LiteLLMModel schema."""

    def test_minimal_creation(self):
        model = LiteLLMModel(
            provider="openai",
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
        )
        assert model.type == "litellm"
        assert model.provider == "openai"
        assert model.model == "gpt-4o"
        assert model.base_url == "https://api.openai.com/v1"
        assert model.api_key == "sk-test"

    def test_full_creation(self):
        model = LiteLLMModel(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            base_url="https://api.anthropic.com",
            api_key="sk-ant-test",
            num_retries=5,
            temperature=0.8,
            completion_kwargs={"max_tokens": 4096},
        )
        assert model.temperature == 0.8
        assert model.num_retries == 5
        assert model.completion_kwargs["max_tokens"] == 4096

    def test_all_valid_providers(self):
        for provider in ("openai", "anthropic", "litellm_proxy"):
            model = LiteLLMModel(
                provider=provider,
                model="some-model",
                base_url="https://api.example.com/v1",
                api_key="sk-test",
            )
            assert model.provider == provider

    def test_invalid_provider(self):
        with pytest.raises(ValidationError):
            LiteLLMModel(
                provider="unknown-provider",
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            LiteLLMModel(
                provider="openai",
                model="gpt-4o",
                # Missing base_url and api_key
            )

    def test_wrong_type_literal(self):
        with pytest.raises(ValidationError):
            LiteLLMModel(
                type="other",
                provider="openai",
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            LiteLLMModel(
                provider="openai",
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
                extra_field="not_allowed",
            )

    def test_temperature_range(self):
        for temp in [0.0, 0.5, 1.0]:
            model = LiteLLMModel(
                provider="openai",
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
                temperature=temp,
            )
            assert model.temperature == temp

    def test_temperature_out_of_range(self):
        with pytest.raises(ValidationError):
            LiteLLMModel(
                provider="openai",
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
                temperature=1.5,
            )

    def test_serialization_roundtrip(self):
        original = LiteLLMModel(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            base_url="https://api.anthropic.com",
            api_key="sk-ant-test",
            temperature=0.8,
        )
        data = original.model_dump()
        restored = LiteLLMModel.model_validate(data)
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.temperature == original.temperature

    def test_json_serialization(self):
        model = LiteLLMModel(
            provider="openai",
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
        )
        json_str = model.model_dump_json()
        assert "gpt-4o" in json_str
        restored = LiteLLMModel.model_validate_json(json_str)
        assert restored.model == "gpt-4o"


# ============================================================================
# Model Union (discriminated by "type")
# ============================================================================


@pytest.mark.unit
class TestModelUnion:
    """Tests for the Model discriminated union type."""

    def test_openai_discriminated(self):
        data = {"type": "openai", "model": "gpt-4o", "api_key": "sk-test"}
        from pydantic import TypeAdapter
        ta = TypeAdapter(Model)
        model = ta.validate_python(data)
        assert isinstance(model, OpenAIModel)
        assert model.type == "openai"

    def test_anthropic_discriminated(self):
        data = {"type": "anthropic", "model": "claude-3-5-sonnet-latest", "api_key": "sk-ant-test"}
        from pydantic import TypeAdapter
        ta = TypeAdapter(Model)
        model = ta.validate_python(data)
        assert isinstance(model, AnthropicModel)
        assert model.type == "anthropic"

    def test_litellm_discriminated(self):
        data = {
            "type": "litellm",
            "provider": "openai",
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
        }
        from pydantic import TypeAdapter
        ta = TypeAdapter(Model)
        model = ta.validate_python(data)
        assert isinstance(model, LiteLLMModel)

    def test_unknown_type_raises(self):
        data = {"type": "unknown", "model": "x", "api_key": "k"}
        from pydantic import TypeAdapter
        ta = TypeAdapter(Model)
        with pytest.raises(ValidationError):
            ta.validate_python(data)

    def test_serialization_preserves_type_field(self):
        model = LiteLLMModel(
            provider="openai",
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
        )
        data = model.model_dump()
        assert data["type"] == "litellm"
