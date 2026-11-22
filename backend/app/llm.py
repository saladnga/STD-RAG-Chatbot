"""
The one place OpenAI clients are created, so every call gets the same timeout and retry policy. The SDK default is a 600s timeout: a chat reply could hang 10 minutes.
"""

from openai import AsyncOpenAI, OpenAI

TIMEOUT_S = 30.0 # max silence from OpenAI (between stream chunks), not total reply time
MAX_RETRIES = 2  # SDK retries connection errors, 429 and 5xx with backoff; never 401/400
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-ada-002"  # changing it means re-embedding every stored chunk


def async_client(api_key: str | None, timeout: float = TIMEOUT_S, max_retries: int = MAX_RETRIES) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)


def sync_client(api_key: str | None, timeout: float = TIMEOUT_S, max_retries: int = MAX_RETRIES) -> OpenAI:
    return OpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)