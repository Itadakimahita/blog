import logging
from typing import Any, Dict

from rest_framework_simplejwt.views import TokenObtainPairView

from apps.abstracts.rate_limit import (
    client_ip_from_request,
    is_rate_limited,
    too_many_requests_response,
)
from apps.users.jwt import LoggingTokenObtainPairSerializer


logger = logging.getLogger("users")


class RateLimitedTokenObtainPairView(TokenObtainPairView):
    """A view that extends the TokenObtainPairView to include rate limiting based on the client's IP address."""
    serializer_class = LoggingTokenObtainPairSerializer

    def post(self, request: Any, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> Any:
        ip_address = client_ip_from_request(request)
        if is_rate_limited(
            key=f"rl:token:ip:{ip_address}",
            limit=10,
            window_seconds=60,
        ):
            logger.warning("Rate limit exceeded for token endpoint ip=%s", ip_address)
            return too_many_requests_response()
        return super().post(request, *args, **kwargs)
