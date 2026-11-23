"""Login checks accept Firebase tokens and ignore unverified emails."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

import main
from api import deps
from api.deps import require_admin_auth

client = TestClient(main.app)


def _firebase(claims=None, error=None):
    """Pretend Firebase verified (claims) or rejected (error) the token."""
    return patch.object(deps.firebase_auth, "verify_id_token", side_effect=error, return_value=claims)


def test_firebase_token_gives_user_id_and_email():
    with _firebase({"uid": "fb-123", "email": "a@b.com", "email_verified": True}):
        assert deps._verify_user_token("tok") == {"id": "fb-123", "email": "a@b.com"}


def test_unverified_email_is_dropped():
    with _firebase({"uid": "fb-123", "email": "admin@b.com", "email_verified": False}):
        assert deps._verify_user_token("tok") == {"id": "fb-123", "email": None}


def test_rejected_token_is_401():
    with _firebase(error=ValueError("bad")):
        r = client.post("/rag/ask", json={"question": "hi"}, headers={"Authorization": "Bearer junk"})
    assert r.status_code == 401


def test_unverified_email_cannot_pass_admin_check():
    check = require_admin_auth(allow_unauthenticated=False, allowed_emails={"admin@b.com"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")
    with _firebase({"uid": "fb-x", "email": "admin@b.com", "email_verified": False}), \
         pytest.raises(HTTPException) as refused:
        asyncio.run(check(creds))
    assert refused.value.status_code == 403
