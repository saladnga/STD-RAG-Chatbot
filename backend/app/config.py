"""
Every setting the server reads, in one typed place. Values come from environment variables
(Cloud Run sets them from the Console and Secret Manager) or, locally, from app/.env.
A missing required value stops the server at startup instead of failing on the first request.
"""

from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _comma_list(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env", extra="ignore")

    openai_api_key: str
    # Comma-separated in the environment, e.g. https://your-app.vercel.app,http://localhost:5173
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    # Accounts that may call /rag/upload. Empty means any logged-in user.
    admin_emails: Annotated[set[str], NoDecode] = set()
    allow_unauthenticated_rag_upload: bool = False  # local development only
    firebase_project_id: str = "troy-healthlink"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        return _comma_list(value)

    @field_validator("admin_emails", mode="before")
    @classmethod
    def _split_emails(cls, value: object) -> object:
        value = _comma_list(value)
        return {email.lower() for email in value} if isinstance(value, list) else value


settings = Settings()  # pyright: ignore[reportCallIssue]  # required fields come from the environment
