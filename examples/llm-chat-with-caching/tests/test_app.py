"""Tests for LLM Chat App with Crucible Caching"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app import app, cache_metrics, ChatRequest, Message

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint():
    """Test root endpoint returns info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "endpoints" in data
    assert data["name"] == "LLM Chat with Crucible Caching"


@patch("app.client.chat.completions.create")
def test_chat_request_success(mock_create):
    """Test successful chat request."""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.id = "chatcmpl-123"
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello! How can I help?"
    mock_response.usage.completion_tokens = 10
    mock_create.return_value = mock_response

    # Make request
    response = client.post(
        "/chat",
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "chatcmpl-123"
    assert data["content"] == "Hello! How can I help?"
    assert data["tokens_used"] == 10
    assert "latency_ms" in data
    assert "cost" in data


@patch("app.client.chat.completions.create")
def test_chat_with_multiple_messages(mock_create):
    """Test chat with conversation history."""
    mock_response = MagicMock()
    mock_response.id = "chatcmpl-456"
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "The capital of France is Paris."
    mock_response.usage.completion_tokens = 12
    mock_create.return_value = mock_response

    response = client.post(
        "/chat",
        json={
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "What is the capital of France?"},
                {"role": "assistant", "content": "I'll tell you about France's capital."},
                {"role": "user", "content": "And what's the population?"},
            ],
            "temperature": 0.5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["content"]) > 0


def test_metrics_endpoint():
    """Test metrics endpoint returns correct structure."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "cache_hits" in data
    assert "cache_hit_rate" in data
    assert "l1_hits" in data
    assert "l2_hits" in data
    assert "total_tokens_saved" in data
    assert "total_cost_saved" in data


@patch("app.client.chat.completions.create")
def test_cache_hit_detection(mock_create):
    """Test that fast responses are detected as cache hits."""
    import time

    mock_response = MagicMock()
    mock_response.id = "chatcmpl-789"
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Cached response"
    mock_response.usage.completion_tokens = 5
    mock_create.return_value = mock_response

    # Mock fast response (cache hit)
    def mock_delay(*args, **kwargs):
        time.sleep(0.005)  # 5ms = cache hit threshold
        return mock_response

    mock_create.side_effect = mock_delay

    response = client.post(
        "/chat",
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "latency_ms" in data
    # Note: actual caching logic is in Crucible, not this app
    # We're just verifying the response structure


def test_cost_calculation():
    """Test cost is calculated correctly."""
    # GPT-4: $0.00002 per token
    tokens = 100
    expected_cost = tokens * 0.00002  # $0.002

    with patch("app.client.chat.completions.create") as mock_create:
        mock_response = MagicMock()
        mock_response.id = "chatcmpl-cost"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test"
        mock_response.usage.completion_tokens = tokens
        mock_create.return_value = mock_response

        response = client.post(
            "/chat",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert abs(data["cost"] - expected_cost) < 0.00001  # Allow rounding


@patch("app.client.chat.completions.create")
def test_error_handling(mock_create):
    """Test error handling for failed requests."""
    mock_create.side_effect = Exception("API Error")

    response = client.post(
        "/chat",
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 500
    assert "failed" in response.json()["detail"].lower()


def test_metrics_accumulation():
    """Test that metrics accumulate correctly."""
    initial_requests = cache_metrics.total_requests

    with patch("app.client.chat.completions.create") as mock_create:
        mock_response = MagicMock()
        mock_response.id = "chatcmpl-metric"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test"
        mock_response.usage.completion_tokens = 10
        mock_create.return_value = mock_response

        # Make 3 requests
        for _ in range(3):
            client.post(
                "/chat",
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": "Hi"}],
                },
            )

        assert cache_metrics.total_requests == initial_requests + 3
