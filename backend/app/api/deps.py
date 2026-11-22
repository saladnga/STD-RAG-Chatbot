"""
What every request goes through before an endpoint runs: the login check, the admin check,
and rate limits.
"""

import asyncio
import logging
from typing import Optional, Dict

import limits
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
from slowapi import Limiter

import store  # noqa: F401  # initializes the Firebase app the token check below uses
from config import settings

logger = logging.getLogger(__name__)

ALLOW_UNAUTHENTICATED_RAG_UPLOAD = settings.allow_unauthenticated_rag_upload
# Empty means "any logged-in user" - only endpoints that pass this into
# require_admin_auth actually enforce it.
ADMIN_EMAILS = settings.admin_emails


# --- Login check ---

def _verify_user_token(token: str) -> Optional[Dict]:
    if not token:
        return None
    try:
        # No key file: verifying a login only needs Google's public keys, which the SDK fetches and caches.
        claims = firebase_auth.verify_id_token(token)
    except Exception:
        return None  # not a (valid) Firebase token
    # Anyone can sign up with any address, so an unverified email must not count -
    # otherwise a stranger could register an ADMIN_EMAILS address and pass the admin check.
    email = claims.get("email") if claims.get("email_verified") else None
    return {"id": claims["uid"], "email": email}


async def verify_user_token(token: str) -> Optional[Dict]:
    return await asyncio.to_thread(_verify_user_token, token)


# --- Rate limits ---

def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)


def enforce(limit: str, endpoint: str, user_id: str) -> None:
    """Per-user limit for logged-in endpoints. Raises 429 when exceeded."""
    if not limiter.limiter.hit(limits.parse(limit), endpoint, user_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")


# --- Admin check ---

security = HTTPBearer(auto_error=False)  # Don't auto-raise error, handle manually


def require_admin_auth(
    allow_unauthenticated: bool, allowed_emails: Optional[set] = None
):
    """
    Dependency factory for admin-only endpoints (document upload):
    requires a valid Bearer token, unless the given dev-mode flag allows
    bypassing it locally, optionally narrowed to a specific email allowlist.
    Shared so every caller gets the same (correctly awaited) token check,
    rather than each router re-implementing its own.
    """

    async def verify(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> Dict:
        if allow_unauthenticated:
            logger.warning(
                "Admin endpoint accessible without authentication (dev mode)"
            )
            return {"id": "dev_user", "role": "admin"}

        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please provide a valid Bearer token.",
            )

        user = await verify_user_token(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if allowed_emails and (user.get("email") or "").lower() not in allowed_emails:
            raise HTTPException(
                status_code=403, detail="This account isn't authorized for this action."
            )

        return user

    return verify


require_user = require_admin_auth(allow_unauthenticated=False)  # any logged-in user
