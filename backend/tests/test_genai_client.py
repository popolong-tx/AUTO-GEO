"""Tests for OCI GenAI client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.genai_client import GenAIClient, SUPPORTED_MODELS, DEFAULT_MODEL


def test_supported_models():
    assert "xai.grok-4.20-multi-agent-0309" in SUPPORTED_MODELS
    assert "xai.grok-4.3" in SUPPORTED_MODELS


def test_default_model():
    client = GenAIClient(api_key="test", base_url="http://test")
    assert client.default_model == DEFAULT_MODEL


def test_get_model_id_default():
    client = GenAIClient(api_key="test", base_url="http://test")
    assert client.get_model_id() == DEFAULT_MODEL


def test_get_model_id_specific():
    client = GenAIClient(api_key="test", base_url="http://test")
    assert client.get_model_id("xai.grok-4.3") == "xai.grok-4.3"


def test_get_model_id_fallback():
    client = GenAIClient(api_key="test", base_url="http://test")
    assert client.get_model_id("unknown-model") == DEFAULT_MODEL


def test_list_models():
    client = GenAIClient(api_key="test", base_url="http://test")
    models = client.list_models()
    assert len(models) == 2
    assert models[0]["id"] == "xai.grok-4.20-multi-agent-0309"


@pytest.mark.asyncio
async def test_analyze():
    client = GenAIClient(api_key="test", base_url="http://test")
    mock_response = MagicMock()
    mock_response.output_text = "Test response"

    with patch.object(client.client.responses, 'create', new_callable=AsyncMock, return_value=mock_response):
        result = await client.analyze("test prompt")
        assert result == "Test response"
