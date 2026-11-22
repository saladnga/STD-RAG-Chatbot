"""
Data access for user profiles, chat sessions, messages, and token verification. Lives at the app root (not under routers/) because it's shared plumbing, not a router.

Firestore layout - each user's data lives under their own document, so one user's
query can never reach another user's chats:
    users/{uid}                                  profile
    users/{uid}/sessions/{session_id}            one chat
    users/{uid}/sessions/{session_id}/messages/  its messages
"""

from datetime import datetime, timezone
from functools import cache
from supabase_client import get_supabase_client
from typing import Optional, List, Dict
import asyncio

import firebase_admin
from firebase_admin import auth as firebase_auth, firestore_async
from google.api_core.exceptions import NotFound
from google.cloud.firestore_v1 import Query

FIREBASE_PROJECT_ID = "troy-healthlink"
# No key file: verifying a login only needs Google's public keys, which the SDK fetches and caches.
firebase_admin.initialize_app(options={"projectId": FIREBASE_PROJECT_ID})


def _verify_firebase_token(token: str) -> Optional[Dict]:
    try:
        claims = firebase_auth.verify_id_token(token)
    except Exception:
        return None  # not a (valid) Firebase token
    # Anyone can sign up with any address, so an unverified email must not count -
    # otherwise a stranger could register an ADMIN_EMAILS address and pass the admin check.
    email = claims.get("email") if claims.get("email_verified") else None
    return {"id": claims["uid"], "email": email}


def _verify_user_token(token: str) -> Optional[Dict]:
    if not token:
        return None
    # Supabase fallback until every user is on Firebase; delete it with Supabase.
    user = _verify_firebase_token(token)
    if user:
        return user
    try:
        supabase = get_supabase_client()
        # Validates this token directly - must NOT use set_session, which would mutate the shared client's identity for every other request.
        user_res = supabase.auth.get_user(token)

        if user_res and user_res.user:
            return {"id": user_res.user.id, "email": user_res.user.email}
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None
    return None


async def verify_user_token(token: str) -> Optional[Dict]:
    return await asyncio.to_thread(_verify_user_token, token)


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
