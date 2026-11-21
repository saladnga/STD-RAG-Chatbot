import limits
from fastapi import HTTPException, Request
from slowapi import Limiter


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