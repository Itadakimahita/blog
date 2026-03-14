import logging
from typing import Any, Dict

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_429_TOO_MANY_REQUESTS

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from apps.abstracts.rate_limit import (
    client_ip_from_request,
    is_rate_limited,
    too_many_requests_response,
)
from apps.users.jwt import LoggingTokenObtainPairSerializer
from apps.abstracts.serializers import ErrorDetailSerializer


logger = logging.getLogger("users")


class RateLimitedTokenObtainPairView(TokenObtainPairView):
    """A view that extends the TokenObtainPairView to include rate limiting based on the client's IP address."""
    serializer_class = LoggingTokenObtainPairSerializer

    @extend_schema(
        summary="Obtain JWT token pair",
        description=(
            "Authenticates a user and returns a JWT access/refresh token pair.\n\n"
            "Authentication: not required.\n"
            "Side effects: none.\n"
            "Language/timezone: validation and error strings are localized using the active request language.\n"
            "Rate limiting: returns 429 when too many attempts are made from the same IP."
        ),
        tags=["Auth"],
        request=OpenApiTypes.OBJECT,
        responses={
            HTTP_200_OK: OpenApiResponse(response=OpenApiTypes.OBJECT),
            HTTP_400_BAD_REQUEST: OpenApiResponse(response=OpenApiTypes.OBJECT),
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_429_TOO_MANY_REQUESTS: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"email": "test@example.com", "password": "Str0ngPassw0rd!"},
            ),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={"refresh": "<jwt-refresh-token>", "access": "<jwt-access-token>"},
            ),
            OpenApiExample(
                "401 Response Example",
                response_only=True,
                status_codes=[str(HTTP_401_UNAUTHORIZED)],
                value={"detail": "No active account found with the given credentials"},
            ),
            OpenApiExample(
                "429 Response Example",
                response_only=True,
                status_codes=[str(HTTP_429_TOO_MANY_REQUESTS)],
                value={"detail": "Too many requests. Try again later."},
            ),
        ],
    )
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
