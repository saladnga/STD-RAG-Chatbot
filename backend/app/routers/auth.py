# Signup, login and password resets happen in the browser with Firebase; this router only serves the profile.
import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from openai import AuthenticationError
from llm_clients import async_client
from db import verify_user_token, get_user_openai_settings, get_profile as load_profile, save_profile
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _strip_openai_key(profile: dict) -> dict:
    # Never let the raw key reach the frontend - it gets persisted straight into localStorage. Swap it for a boolean the UI can show status from.
    profile["has_custom_openai_key"] = bool(profile.pop("openai_api_key", None))
    return profile


# GET current user's profile
@router.get("/profile")
async def get_profile(authorization: Optional[str] = Header(None)):
    """
    Retrieve the authenticated user's profile.
    Requires Authorization: Bearer <token>
    """
    if not authorization:
        # Explicit 401 instead of FastAPI 422 when header missing
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    profile = await load_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _strip_openai_key(profile)


# Also creates the profile - signup calls this right after Firebase makes the account.
@router.patch("/profile")
async def update_profile(profile_update: dict, authorization: str = Header(...)):
    """
    Partial update to the current user's profile.
    Example payload: { "first_name": "Ava", "phone": "555-1234" }
    """
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not profile_update:
        raise HTTPException(status_code=400, detail="No update data provided")

    # The key and model have their own validated endpoint below - never settable through this generic passthrough.
    for field in ("openai_api_key", "openai_model", "user_id"):
        profile_update.pop(field, None)
    await save_profile(user["id"], profile_update)
    return _strip_openai_key(await load_profile(user["id"]) or {})


# Kept small and explicit, not any string - this becomes a real API call.
# chat.py imports this same list for its fallback.
ALLOWED_CUSTOM_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
DEFAULT_CUSTOM_MODEL = "gpt-4o"


class OpenAIKeyRequest(BaseModel):
    api_key: Optional[str] = None  # omit/empty to update the model only (see below) - use DELETE to clear
    model: Optional[str] = None  # defaults to DEFAULT_CUSTOM_MODEL when omitted


@router.put("/openai-key")
async def set_openai_key(body: OpenAIKeyRequest, authorization: str = Header(...)):
    """
    Set a personal OpenAI API key (+ model), or - with api_key omitted and a
    key already on file - change just the model choice without re-submitting
    the key. Use DELETE /auth/openai-key to actually clear it; this endpoint
    never clears on its own, so there's no ambiguity between "not provided"
    and "please remove." Never returns the raw key back - see
    _strip_openai_key - only has_custom_openai_key/openai_model.
    """
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    submitted_key = (body.api_key or "").strip() or None

    if submitted_key:
        model = body.model if body.model in ALLOWED_CUSTOM_MODELS else DEFAULT_CUSTOM_MODEL
        # Validate before storing - a bad/revoked key should fail loudly
        # here, not confusingly mid-conversation later.
        try:
            await async_client(submitted_key, timeout=10.0, max_retries=0).models.list()
        except AuthenticationError:
            raise HTTPException(status_code=400, detail="That API key was rejected by OpenAI - double check it.")
        except Exception as e:
            logger.warning(f"OpenAI key validation error: {e}")
            raise HTTPException(status_code=400, detail="Could not verify that API key right now. Please try again.")

        await save_profile(user["id"], {"openai_api_key": submitted_key, "openai_model": model})
        return {"has_custom_openai_key": True, "openai_model": model}

    # No new key submitted - a model-only change, but only meaningful if a
    # key is already on file to pair it with.
    existing_key, _ = await get_user_openai_settings(user["id"])
    if not existing_key:
        raise HTTPException(status_code=400, detail="No API key on file yet - add one first.")
    if body.model not in ALLOWED_CUSTOM_MODELS:
        raise HTTPException(status_code=400, detail="Unrecognized model choice.")

    await save_profile(user["id"], {"openai_api_key": existing_key, "openai_model": body.model})
    return {"has_custom_openai_key": True, "openai_model": body.model}


@router.delete("/openai-key")
async def clear_openai_key(authorization: str = Header(...)):
    """Remove the current user's personal API key and model choice entirely."""
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    await save_profile(user["id"], {"openai_api_key": None, "openai_model": None})
    return {"has_custom_openai_key": False, "openai_model": None}
