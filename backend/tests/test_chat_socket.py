import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import main
import routers.chat as chat

SORRY = "Sorry, something went wrong on our side. Please try again."


@pytest.fixture
def client(monkeypatch):
    """A chat socket with every database and network call replaced by a fake."""

    async def fake_verify(token):
        return {"id": "user-1", "email": "user@example.com"} if token == "good" else None

    async def fake_settings(user_id):
        return None, None  # no personal OpenAI key

    async def fake_session(user_id, session_id, token):
        return {"id": "session-1"}

    async def fake_history(session_id):
        return []

    async def do_nothing(*args, **kwargs):
        return None

    def no_database():
        raise RuntimeError("no database in tests")

    monkeypatch.setattr(chat, "verify_user_token", fake_verify)
    monkeypatch.setattr(chat, "get_user_openai_settings", fake_settings)
    monkeypatch.setattr(chat, "get_or_create_session", fake_session)
    monkeypatch.setattr(chat, "load_chat_history", fake_history)
    monkeypatch.setattr(chat, "save_message", do_nothing)
    monkeypatch.setattr(chat, "update_session_title", do_nothing)
    monkeypatch.setattr(chat, "get_supabase_client", no_database)
    monkeypatch.setattr(main.app.state, "model", None, raising=False)
    monkeypatch.setattr(main.app.state, "label_encoder", None, raising=False)
    return TestClient(main.app)


def test_bad_token_closes_with_4001(client):
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect("/ws/chat?token=bad") as ws:
            ws.receive_text()
    assert closed.value.code == 4001


def test_too_long_message_is_a_complete_reply(client):
    with client.websocket_connect("/ws/chat?token=good") as ws:
        assert ws.receive_text() == "__SESSION__:session-1"
        ws.send_text("x" * 2001)
        assert ws.receive_text().startswith("Message too long")
        assert ws.receive_text() == "__DONE__"


def test_rate_limited_message_is_a_complete_reply(client, monkeypatch):
    monkeypatch.setattr(chat.limiter.limiter, "hit", lambda *args: False)
    with client.websocket_connect("/ws/chat?token=good") as ws:
        ws.receive_text()
        ws.send_text("hello")
        assert ws.receive_text().startswith("You are sending messages too fast")
        assert ws.receive_text() == "__DONE__"


def test_unexpected_error_sends_safe_reply_and_keeps_socket_open(client, monkeypatch):
    async def crash(*args, **kwargs):
        raise RuntimeError("postgres://admin:secret-password@db.internal")

    monkeypatch.setattr(chat, "get_rag_context_for_chat", crash)
    with client.websocket_connect("/ws/chat?token=good") as ws:
        ws.receive_text()
        for _ in range(2):  # the second round proves the socket survived the first crash
            ws.send_text("hello")
            reply = ws.receive_text()
            assert reply == SORRY
            assert "secret-password" not in reply
            assert ws.receive_text() == "__DONE__"


def test_history_load_failure_sends_safe_reply(client, monkeypatch):
    async def crash(session_id):
        raise RuntimeError("history table unreachable")

    monkeypatch.setattr(chat, "load_chat_history", crash)
    with client.websocket_connect("/ws/chat?token=good") as ws:
        assert ws.receive_text() == "Could not load this chat. Please refresh and try again."
        assert ws.receive_text() == "__DONE__"
