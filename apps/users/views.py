# Python modules
from typing import Any, Dict
import logging

# Django modules
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

# Django REST Framework
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request as DRFRequest
from rest_framework.response import Response as DRFResponse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_429_TOO_MANY_REQUESTS,
)
from rest_framework.decorators import action

# DRF Spectacular
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

# Project modules
from apps.users.models import CustomUser
from apps.users.serializers import (
    UserDetailSerializer,
    UserRegisterSerializer,
    UserPreferredLanguageSerializer,
    UserTimezoneSerializer,
)
from apps.users.caches import PreferredLanguageCacheAccessor, PreferredTimezoneCacheAccessor
from apps.abstracts.rate_limit import (
    client_ip_from_request,
    is_rate_limited,
    too_many_requests_response,
)
from apps.abstracts.serializers import ( 
    ErrorDetailSerializer, ValidationErrorSerializer, MessageSerializer, 
)


logger = logging.getLogger("users")


class UserViewSet(GenericViewSet):
    """
    User-related endpoints (registration and profile preferences).
    """

    permission_classes = [AllowAny]
    queryset = CustomUser.objects.all()
    serializer_class = UserDetailSerializer

    def get_serializer_class(self):
        if getattr(self, "action", None) == "register":
            return UserRegisterSerializer
        if getattr(self, "action", None) == "set_preferred_language":
            return UserPreferredLanguageSerializer
        if getattr(self, "action", None) == "set_timezone":
            return UserTimezoneSerializer
        return UserDetailSerializer

    @extend_schema(
        summary="List users",
        description=(
            "Returns a list of all users.\n\n"
            "Authentication: not required.\n"
            "Side effects: none.\n"
            "Language/timezone: response strings are localized using the active request language."
        ),
        tags=["Auth"],
        responses={
            HTTP_200_OK: UserDetailSerializer(many=True),
            HTTP_404_NOT_FOUND: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value=[
                    {
                        "id": 1,
                        "email": "test@example.com",
                        "first_name": "Dias",
                        "last_name": "Kad",
                        "avatar": None,
                        "preferred_language": "en",
                        "timezone": "UTC",
                    }
                ],
            ),
            OpenApiExample(
                "404 Response Example",
                response_only=True,
                status_codes=[str(HTTP_404_NOT_FOUND)],
                value={"detail": "No users found."},
            ),
        ],
    )
    def list(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> DRFResponse:
        logger.debug("List users request received")
        try:
            users: QuerySet[CustomUser] = CustomUser.objects.all()
            if not users.exists():
                logger.warning("List users requested but no users found")
                return DRFResponse({"detail": _("No users found.")}, status=HTTP_404_NOT_FOUND)
            serializer: UserDetailSerializer = UserDetailSerializer(users, many=True)
            logger.info("List users success. Count=%s", users.count())
            return DRFResponse(serializer.data, status=HTTP_200_OK)
        except Exception:
            logger.exception("Unhandled exception while listing users")
            raise

    @extend_schema(
        summary="Register user",
        description=(
            "Creates a new user account and returns JWT tokens.\n\n"
            "Authentication: not required.\n"
            "Side effects:\n"
            "- Sends a welcome email rendered from templates in the language selected at registration.\n"
            "- Stores preferred language and timezone in the user profile.\n\n"
            "Language/timezone:\n"
            "- Validation errors and response strings are localized using the active request language.\n"
            "- The welcome email language is forced to the registration language, independent of the active request language.\n\n"
            "Rate limiting:\n"
            "- Returns 429 when too many registration attempts are made from the same IP."
        ),
        tags=["Auth"],
        request=UserRegisterSerializer,
        responses={
            HTTP_201_CREATED: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="User created; tokens returned.",
            ),
            HTTP_400_BAD_REQUEST: ValidationErrorSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
            HTTP_429_TOO_MANY_REQUESTS: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={
                    "email": "new@example.com",
                    "first_name": "Aruzhan",
                    "last_name": "Bek",
                    "password": "Str0ngPassw0rd!",
                    "preferred_language": "ru",
                    "timezone": "Asia/Almaty",
                },
            ),
            OpenApiExample(
                "201 Response Example",
                response_only=True,
                status_codes=[str(HTTP_201_CREATED)],
                value={
                    "email": "new@example.com",
                    "first_name": "Aruzhan",
                    "last_name": "Bek",
                    "preferred_language": "ru",
                    "timezone": "Asia/Almaty",
                    "access": "<jwt-access-token>",
                    "refresh": "<jwt-refresh-token>",
                },
            ),
            OpenApiExample(
                "400 Response Example",
                response_only=True,
                status_codes=[str(HTTP_400_BAD_REQUEST)],
                value={"email": ["Enter a valid email address."]},
            ),
            OpenApiExample(
                "429 Response Example",
                response_only=True,
                status_codes=[str(HTTP_429_TOO_MANY_REQUESTS)],
                value={"detail": "Too many requests. Try again later."},
            ),
        ],
    )
    @action(
        methods=["post"],
        detail=False,
        permission_classes=[AllowAny],
        url_name="register",
        url_path="register",
    )
    def register(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> DRFResponse:
        email = request.data.get("email")
        ip_address = client_ip_from_request(request)
        if is_rate_limited(
            key=f"rl:register:ip:{ip_address}",
            limit=5,
            window_seconds=60,
        ):
            logger.warning("Rate limit exceeded for register endpoint ip=%s", ip_address)
            return too_many_requests_response()
        logger.info("Registration attempt for email: %s", email)
        try:
            serializer: UserRegisterSerializer = UserRegisterSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(
                    "Registration failed validation for email: %s errors=%s",
                    email,
                    serializer.errors,
                )
                return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
            user: CustomUser = serializer.save()
            refresh: str = serializer.get_refresh(user)
            access: str = serializer.get_access(user)
            logger.info("User registered: %s", user.email)
            return DRFResponse(
                {**serializer.data, "refresh": refresh, "access": access},
                status=HTTP_201_CREATED,
            )
        except Exception:
            logger.exception("Registration failed with exception for email: %s", email)
            raise

    @extend_schema(
        summary="Get current user",
        description=(
            "Returns the authenticated user's profile.\n\n"
            "Authentication: required (JWT).\n"
            "Side effects: none.\n"
            "Language/timezone: response strings are localized using the active request language."
        ),
        tags=["Auth"],
        responses={
            HTTP_200_OK: UserDetailSerializer,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={
                    "id": 1,
                    "email": "test@example.com",
                    "first_name": "Dias",
                    "last_name": "Kad",
                    "avatar": None,
                    "preferred_language": "en",
                    "timezone": "UTC",
                },
            )
        ],
    )
    @action(
        methods=["get"],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path="me",
        url_name="me",
    )
    def me(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> DRFResponse:
        serializer: UserDetailSerializer = UserDetailSerializer(request.user)
        return DRFResponse(serializer.data, status=HTTP_200_OK)

    @extend_schema(
        summary="Update preferred language",
        description=(
            "Updates the authenticated user's preferred language.\n\n"
            "Authentication: required (JWT).\n"
            "Side effects: updates the user profile and refreshes the cached preference used by middleware.\n"
            "Language/timezone: validation errors and success messages are localized using the active request language."
        ),
        tags=["Auth"],
        request=UserPreferredLanguageSerializer,
        responses={
            HTTP_200_OK: OpenApiResponse(response=OpenApiTypes.OBJECT),
            HTTP_400_BAD_REQUEST: ValidationErrorSerializer,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"preferred_language": "kk"},
            ),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={"detail": "Preferred language updated.", "preferred_language": "kk"},
            ),
            OpenApiExample(
                "400 Response Example",
                response_only=True,
                status_codes=[str(HTTP_400_BAD_REQUEST)],
                value={"preferred_language": ["Unsupported language. Supported: en, ru, kk."]},
            ),
        ],
    )
    @action(
        methods=["patch"],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path="me/language",
        url_name="me-language",
    )
    def set_preferred_language(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> DRFResponse:
        serializer = UserPreferredLanguageSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user: CustomUser = serializer.save()
        PreferredLanguageCacheAccessor.set(user_id=user.id, preferred_language=user.preferred_language)
        return DRFResponse(
            {"detail": _("Preferred language updated."), "preferred_language": user.preferred_language},
            status=HTTP_200_OK,
        )

    @extend_schema(
        summary="Update timezone",
        description=(
            "Updates the authenticated user's timezone (IANA identifier).\n\n"
            "Authentication: required (JWT).\n"
            "Side effects: updates the user profile and refreshes the cached preference used by middleware.\n"
            "Language/timezone: validation errors and success messages are localized using the active request language."
        ),
        tags=["Auth"],
        request=UserTimezoneSerializer,
        responses={
            HTTP_200_OK: OpenApiResponse(response=OpenApiTypes.OBJECT),
            HTTP_400_BAD_REQUEST: ValidationErrorSerializer,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"timezone": "Asia/Almaty"},
            ),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={"detail": "Timezone updated.", "timezone": "Asia/Almaty"},
            ),
            OpenApiExample(
                "400 Response Example",
                response_only=True,
                status_codes=[str(HTTP_400_BAD_REQUEST)],
                value={
                    "timezone": [
                        "Invalid timezone. Use a valid IANA identifier (e.g. 'UTC' or 'Asia/Almaty')."
                    ]
                },
            ),
        ],
    )
    @action(
        methods=["patch"],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path="me/timezone",
        url_name="me-timezone",
    )
    def set_timezone(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> DRFResponse:
        serializer = UserTimezoneSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user: CustomUser = serializer.save()
        PreferredTimezoneCacheAccessor.set(user_id=user.id, timezone_name=user.timezone)
        return DRFResponse(
            {"detail": _("Timezone updated."), "timezone": user.timezone},
            status=HTTP_200_OK,
        )
