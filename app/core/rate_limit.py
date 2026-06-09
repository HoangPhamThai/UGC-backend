from fastapi import Request
from slowapi import Limiter

from app.core.settings import settings


def _client_ip(request: Request) -> str:
    # When fronted by a trusted proxy, the real client IP is the leftmost
    # entry of X-Forwarded-For. If TRUST_FORWARDED_FOR is false (e.g. the
    # service is exposed directly), ignore the header so callers can't
    # spoof their IP and bypass the limit.
    if settings.trust_forwarded_for:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=_client_ip,
    storage_uri=settings.redis_url,
    strategy="fixed-window",
)
