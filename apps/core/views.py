from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response as DRFResponse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)
from rest_framework.views import APIView

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.abstracts.serializers import ErrorDetailSerializer
from apps.users.caches import PreferredLanguageCacheAccessor, PreferredTimezoneCacheAccessor
from apps.users.serializers import UserPreferredLanguageSerializer, UserTimezoneSerializer


class AuthLanguageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update preferred language",
        description=(
            "Updates the authenticated user's preferred language.\n\n"
            "Authentication: required (JWT).\n"
            "Side effects: updates the user profile and refreshes the cached preference used by the locale middleware.\n"
            "Language/timezone: validation errors and success messages are localized using the active request language."
        ),
        tags=["Auth"],
        request=UserPreferredLanguageSerializer,
        responses={
            HTTP_200_OK: OpenApiTypes.OBJECT,
            HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample("Request Example", request_only=True, value={"preferred_language": "ru"}),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={"detail": "Preferred language updated.", "preferred_language": "ru"},
            ),
        ],
    )
    def patch(self, request, *args, **kwargs) -> DRFResponse:
        serializer = UserPreferredLanguageSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user = serializer.save()
        PreferredLanguageCacheAccessor.set(user_id=user.id, preferred_language=user.preferred_language)
        return DRFResponse(
            {"detail": _("Preferred language updated."), "preferred_language": user.preferred_language},
            status=HTTP_200_OK,
        )


class AuthTimezoneAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update timezone",
        description=(
            "Updates the authenticated user's timezone (IANA identifier).\n\n"
            "Authentication: required (JWT).\n"
            "Side effects: updates the user profile and refreshes the cached preference used by the locale middleware.\n"
            "Language/timezone: validation errors and success messages are localized using the active request language."
        ),
        tags=["Auth"],
        request=UserTimezoneSerializer,
        responses={
            HTTP_200_OK: OpenApiTypes.OBJECT,
            HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample("Request Example", request_only=True, value={"timezone": "Asia/Almaty"}),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={"detail": "Timezone updated.", "timezone": "Asia/Almaty"},
            ),
        ],
    )
    def patch(self, request, *args, **kwargs) -> DRFResponse:
        serializer = UserTimezoneSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user = serializer.save()
        PreferredTimezoneCacheAccessor.set(user_id=user.id, timezone_name=user.timezone)
        return DRFResponse({"detail": _("Timezone updated."), "timezone": user.timezone}, status=HTTP_200_OK)
