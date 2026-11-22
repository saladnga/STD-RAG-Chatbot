"""Comma-separated env vars become clean lists, the way Cloud Run and app/.env write them."""

from config import Settings


def test_comma_separated_settings_are_split_and_cleaned(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.vercel.app, http://localhost:5173,")
    monkeypatch.setenv("ADMIN_EMAILS", " Admin@Example.com ,b@example.com")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_RAG_UPLOAD", "false")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.allowed_origins == ["https://app.vercel.app", "http://localhost:5173"]
    assert settings.admin_emails == {"admin@example.com", "b@example.com"}
    assert settings.allow_unauthenticated_rag_upload is False
