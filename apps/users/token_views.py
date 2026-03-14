from __future__ import annotations
from typing import Any

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED
from rest_framework.request import Request as DRFRequest
from rest_framework.response import Response as DRFResponse

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from apps.abstracts.serializers import ErrorDetailSerializer, ValidationErrorSerializer


class DocumentedTokenRefreshView(TokenRefreshView):
    @extend_schema(
        summary="Refresh JWT access token",
        description=(
            "Exchanges a valid refresh token for a new access token.\n\n"
            "Authentication: not required.\n"
            "Side effects: none.\n"
            "Language/timezone: validation and error strings are localized using the active request language."
        ),
        tags=["Auth"],
        request=OpenApiTypes.OBJECT,
        responses={
            HTTP_200_OK: OpenApiResponse(response=OpenApiTypes.OBJECT),
            HTTP_400_BAD_REQUEST: ValidationErrorSerializer,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"refresh": "<jwt-refresh-token>"},
            ),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={"access": "<jwt-access-token>"},
            ),
        ],
    )
    def post(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> DRFResponse:
        return super().post(request, *args, **kwargs)


class DocumentedTokenVerifyView(TokenVerifyView):
    @extend_schema(
        summary="Verify JWT token",
        description=(
            "Verifies that a token is valid.\n\n"
            "Authentication: not required.\n"
            "Side effects: none.\n"
            "Language/timezone: validation and error strings are localized using the active request language."
        ),
        tags=["Auth"],
        request=OpenApiTypes.OBJECT,
        responses={
            HTTP_200_OK: OpenApiResponse(response=OpenApiTypes.OBJECT),
            HTTP_400_BAD_REQUEST: ValidationErrorSerializer,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"token": "<jwt-access-or-refresh-token>"},
            ),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={},
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

