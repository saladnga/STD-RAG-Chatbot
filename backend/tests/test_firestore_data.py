"""Profile endpoint behaviour, plus a real Firestore round trip when Google credentials are available."""

import asyncio
import uuid

import google.auth
from google.auth.exceptions import DefaultCredentialsError
import pytest
from fastapi.testclient import TestClient

import main
import store
from api import profile

client = TestClient(main.app)


def test_profile_endpoint_reads_firestore_and_hides_the_openai_key(monkeypatch):
    async def fake_verify(token):
        return {"id": "u1", "email": "a@b.com"}

    async def fake_profile(user_id):
        return {"user_id": user_id, "first_name": "Ava", "openai_api_key": "sk-secret"}

    monkeypatch.setattr(profile, "verify_user_token", fake_verify)
    monkeypatch.setattr(profile, "load_profile", fake_profile)
    body = client.get("/auth/profile", headers={"Authorization": "Bearer t"}).json()
    assert body == {"user_id": "u1", "first_name": "Ava", "has_custom_openai_key": True}


def _has_google_credentials() -> bool:
    try:
        google.auth.default()
        return True
    except DefaultCredentialsError:
        return False


@pytest.mark.skipif(not _has_google_credentials(), reason="needs `gcloud auth application-default login`")
def test_real_firestore_round_trip():
    user_id = f"test-{uuid.uuid4().hex[:8]}"  # throwaway user, deleted at the end

    async def scenario():
        store._fs.cache_clear()  # a fresh client bound to this event loop
        try:
            await store.save_profile(user_id, {"first_name": "Test", "openai_api_key": "sk-x"})
            assert await store.get_user_openai_settings(user_id) == ("sk-x", None)

            session = await store.get_or_create_session(user_id)
            assert (await store.get_or_create_session(user_id, session["id"]))["id"] == session["id"]
            await store.save_message(session["id"], user_id, "user", "hello")
            await store.save_message(session["id"], user_id, "assistant", "hi there")
            history = await store.load_chat_history(user_id, session["id"])
            assert [m["content"] for m in history] == ["hello", "hi there"]

            assert await store.update_session_title(user_id, session["id"], "Renamed")
            assert [s["title"] for s in await store.get_user_session(user_id)] == ["Renamed"]
            assert not await store.update_session_title("someone-else", session["id"], "x")  # not their session

            assert await store.delete_session(user_id, session["id"])
            assert await store.get_user_session(user_id) == []
        finally:
            await store._fs().recursive_delete(store._user(user_id))

    asyncio.run(scenario())


def test_profile_patch_creates_a_missing_profile(monkeypatch):
    saved = {}

    async def fake_verify(token):
        return {"id": "new-user", "email": None}

    async def fake_save(user_id, fields):
        saved.update(fields)

    async def fake_load(user_id):
        return {"user_id": user_id, **saved} if saved else None

    monkeypatch.setattr(profile, "verify_user_token", fake_verify)
    monkeypatch.setattr(profile, "save_profile", fake_save)
    monkeypatch.setattr(profile, "load_profile", fake_load)
    r = client.patch("/auth/profile", json={"first_name": "Ava", "user_id": "someone-else"},
                     headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json() == {"user_id": "new-user", "first_name": "Ava", "has_custom_openai_key": False}
