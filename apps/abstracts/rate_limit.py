from django.core.cache import cache
from rest_framework.response import Response as DRFResponse
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS


def _safe_cache_incr(key: str, window_seconds: int) -> int:
    """Safely increment a cache key, initializing it if it doesn't exist."""
    if cache.add(key, 1, timeout=window_seconds):
        return 1

    try:
        return int(cache.incr(key))
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return 1


def is_rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    """Check if a given key has exceeded the rate limit."""
    return _safe_cache_incr(key, window_seconds) > limit


def client_ip_from_request(request) -> str:
    """Extract the client's IP address from the request, accounting for possible proxy headers."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def too_many_requests_response() -> DRFResponse:
    """Return a standardized response for rate-limited requests."""
    return DRFResponse(
        {"detail": "Too many requests. Try again later."},
        status=HTTP_429_TOO_MANY_REQUESTS,
    )
