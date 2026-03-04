"""
Tests unitarios para chat_teams_router (endpoints /chat).

Usa mocks del ChatTeamsAgent — no requiere LLM ni MCP reales.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aifoundry.app.core.agenticai.deepagents.chat_teams.streaming import (
    ChatEvent,
    EventType,
    done_event,
    text_event,
    thinking_event,
)


@pytest.fixture
def client():
    """Cliente de test con la app FastAPI completa."""
    from aifoundry.app.main import app

    return TestClient(app)


class TestChatStreamEndpoint:
    """Tests para POST /api/chat."""

    @patch("aifoundry.app.api.chat_teams_router.get_chat_agent")
    def test_chat_returns_sse(self, mock_get_agent, client):
        """POST /api/chat debe retornar SSE stream."""
        mock_agent = MagicMock()

        async def fake_chat(message, thread_id):
            yield thinking_event("Pensando...")
            yield text_event("Respuesta")
            yield done_event(thread_id)

        mock_agent.chat = fake_chat
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/api/chat",
            json={"message": "Hola", "thread_id": "test-sse"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parsear eventos SSE
        lines = response.text.strip().split("\n\n")
        events = []
        for line in lines:
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                events.append(payload)

        assert len(events) >= 3
        types = [e["type"] for e in events]
        assert "thinking" in types
        assert "text" in types
        assert "done" in types

    @patch("aifoundry.app.api.chat_teams_router.get_chat_agent")
    def test_chat_generates_thread_id_if_missing(self, mock_get_agent, client):
        """Si no se envía thread_id, se genera uno."""
        mock_agent = MagicMock()

        async def fake_chat(message, thread_id):
            yield done_event(thread_id)

        mock_agent.chat = fake_chat
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/api/chat",
            json={"message": "Hola"},
        )

        assert response.status_code == 200

    def test_chat_requires_message(self, client):
        """POST /api/chat sin message debe dar 422."""
        response = client.post("/api/chat", json={})
        assert response.status_code == 422


class TestChatSyncEndpoint:
    """Tests para POST /api/chat/sync."""

    @patch("aifoundry.app.api.chat_teams_router.get_chat_agent")
    def test_sync_returns_json(self, mock_get_agent, client):
        """POST /api/chat/sync debe retornar JSON con response."""
        mock_agent = MagicMock()
        mock_agent.chat_sync = AsyncMock(
            return_value={
                "response": "Hola, soy Hefesto",
                "thread_id": "sync-123",
                "tools_used": [],
            }
        )
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/api/chat/sync",
            json={"message": "Hola", "thread_id": "sync-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hola, soy Hefesto"
        assert data["thread_id"] == "sync-123"
        assert "tools_used" in data

    @patch("aifoundry.app.api.chat_teams_router.get_chat_agent")
    def test_sync_handles_error(self, mock_get_agent, client):
        """POST /api/chat/sync con error del agente debe dar 500."""
        mock_agent = MagicMock()
        mock_agent.chat_sync = AsyncMock(side_effect=RuntimeError("Agent crash"))
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/api/chat/sync",
            json={"message": "Provoca error"},
        )

        assert response.status_code == 500


class TestHistoryEndpoint:
    """Tests para GET /api/chat/history/{thread_id}."""

    @patch("aifoundry.app.api.chat_teams_router.get_chat_agent")
    def test_get_history(self, mock_get_agent, client):
        """GET /api/chat/history debe retornar mensajes."""
        mock_agent = MagicMock()
        mock_agent.get_history = AsyncMock(
            return_value=[
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "Hola, soy Hefesto"},
            ]
        )
        mock_get_agent.return_value = mock_agent

        response = client.get("/api/chat/history/test-thread")

        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test-thread"
        assert data["count"] == 2
        assert len(data["messages"]) == 2

    @patch("aifoundry.app.api.chat_teams_router.get_chat_agent")
    def test_get_empty_history(self, mock_get_agent, client):
        """GET /api/chat/history con thread vacío retorna lista vacía."""
        mock_agent = MagicMock()
        mock_agent.get_history = AsyncMock(return_value=[])
        mock_get_agent.return_value = mock_agent

        response = client.get("/api/chat/history/empty-thread")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["messages"] == []


class TestDeleteHistoryEndpoint:
    """Tests para DELETE /api/chat/history/{thread_id}."""

    def test_delete_history(self, client):
        """DELETE /api/chat/history debe retornar ok."""
        response = client.delete("/api/chat/history/some-thread")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["thread_id"] == "some-thread"