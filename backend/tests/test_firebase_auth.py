"""Login checks accept Firebase tokens, fall back to Supabase, and ignore unverified emails."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

import db
import main
from auth_utils import require_admin_auth

client = TestClient(main.app)


def _firebase(claims=None, error=None):
    """Pretend Firebase verified (claims) or rejected (error) the token."""
    return patch.object(db.firebase_auth, "verify_id_token", side_effect=error, return_value=claims)


def test_firebase_token_gives_user_id_and_email():
    with _firebase({"uid": "fb-123", "email": "a@b.com", "email_verified": True}):
        assert db._verify_user_token("tok") == {"id": "fb-123", "email": "a@b.com"}


def test_unverified_email_is_dropped():
    with _firebase({"uid": "fb-123", "email": "admin@b.com", "email_verified": False}):
        assert db._verify_user_token("tok") == {"id": "fb-123", "email": None}


def test_non_firebase_token_falls_back_to_supabase():
    with _firebase(error=ValueError("not a Firebase token")), \
         patch.object(db, "get_supabase_client") as supabase:
        supabase.return_value.auth.get_user.return_value.user.id = "sb-1"
        supabase.return_value.auth.get_user.return_value.user.email = "s@b.com"
        assert db._verify_user_token("tok") == {"id": "sb-1", "email": "s@b.com"}


def test_token_rejected_by_both_is_401():
    with _firebase(error=ValueError("bad")), \
         patch.object(db, "get_supabase_client", side_effect=Exception("bad")):
        r = client.post("/rag/ask", json={"question": "hi"}, headers={"Authorization": "Bearer junk"})
    assert r.status_code == 401


def test_unverified_email_cannot_pass_admin_check():
    check = require_admin_auth(allow_unauthenticated=False, allowed_emails={"admin@b.com"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")
    with _firebase({"uid": "fb-x", "email": "admin@b.com", "email_verified": False}), \
         pytest.raises(HTTPException) as refused:
        asyncio.run(check(creds))
    assert refused.value.status_code == 403
