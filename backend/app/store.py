"""
The one place that reads and writes Firestore: user profiles, chat sessions and messages.

Firestore layout - each user's data lives under their own document, so one user's
query can never reach another user's chats:
    users/{uid}                                  profile
    users/{uid}/sessions/{session_id}            one chat
    users/{uid}/sessions/{session_id}/messages/  its messages
"""

from datetime import datetime, timezone
from functools import cache
from typing import Optional, List, Dict

import firebase_admin
from firebase_admin import firestore_async
from google.api_core.exceptions import NotFound
from google.cloud.firestore_v1 import Query

from config import settings

# No key file: Cloud Run uses its service account, local runs use `gcloud auth application-default login`.
firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})


@cache
def _fs():
    # Created on first use, so importing this module needs no Google credentials (tests, CI).
    # Credentials: the troy-api service account on Cloud Run; `gcloud auth application-default login` locally.
    return firestore_async.client()


def _user(user_id: str):
    return _fs().collection("users").document(user_id)


def _session(user_id: str, session_id: str):
    return _user(user_id).collection("sessions").document(session_id)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Profiles ---

async def get_profile(user_id: str) -> Optional[Dict]:
    """The raw profile, including openai_api_key - callers sending it to the browser must strip that."""
    snap = await _user(user_id).get()
    return {"user_id": user_id, **(snap.to_dict() or {})} if snap.exists else None


async def save_profile(user_id: str, fields: Dict) -> None:
    """Create the profile or update just the given fields."""
    await _user(user_id).set(fields, merge=True)


async def get_user_openai_settings(user_id: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (api_key, model) - either may be None."""
    profile = await get_profile(user_id) or {}
    return profile.get("openai_api_key") or None, profile.get("openai_model") or None


# --- Chat sessions and messages ---

async def get_or_create_session(user_id: str, session_id: Optional[str] = None) -> Dict:
    if session_id:
        snap = await _session(user_id, session_id).get()
        if snap.exists:
            return {"id": snap.id, **(snap.to_dict() or {})}
    ref = _user(user_id).collection("sessions").document()
    now = _now()
    data = {"title": "New Health Consultation", "created_at": now, "updated_at": now}
    await ref.set(data)
    return {"id": ref.id, **data}


async def load_chat_history(user_id: str, session_id: str, limit: int = 50) -> List[Dict]:
    query = (
        _session(user_id, session_id).collection("messages")
        .order_by("created_at")
        .limit(limit)
    )
    return [{"id": doc.id, **(doc.to_dict() or {})} async for doc in query.stream()]


async def save_message(session_id: str, user_id: str, role: str, content: str) -> None:
    now = _now()
    session = _session(user_id, session_id)
    await session.collection("messages").add({"role": role, "content": content, "created_at": now})
    await session.update({"updated_at": now})  # keeps the sidebar sorted by latest activity


async def get_user_session(user_id: str, limit: int = 10) -> List[Dict]:
    query = (
        _user(user_id).collection("sessions")
        .order_by("updated_at", direction=Query.DESCENDING)
        .limit(limit)
    )
    return [{"id": doc.id, **(doc.to_dict() or {})} async for doc in query.stream()]


async def update_session_title(user_id: str, session_id: str, title: str) -> bool:
    """False if this user has no such session."""
    try:
        await _session(user_id, session_id).update({"title": title})
        return True
    except NotFound:
        return False


async def delete_session(user_id: str, session_id: str) -> bool:
    """Deletes the session and all its messages. False if this user has no such session."""
    ref = _session(user_id, session_id)
    if not (await ref.get()).exists:
        return False
    await _fs().recursive_delete(ref)
    return True
