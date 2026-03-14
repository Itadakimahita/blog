# Python modules
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from django.core.handlers.wsgi import WSGIRequest

# Django modules
from django.utils import translation, timezone

# Django REST Framework modules
from rest_framework.request import Request as DRFResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

# Project modules
from apps.users.caches import PreferredLanguageCacheAccessor, PreferredTimezoneCacheAccessor
from apps.users.models import CustomUser
from apps.users.validators import normalize_language_code
from settings.base import ENGLISH_LANGUAGE_CODE


class CustomLocaleMiddleware:
    """
    Determine and activate language + timezone for each request.

    Request language priority:
    1) Authenticated user preferred language
    2) ?lang= query parameter
    3) Accept-Language header
    4) Default EN
    """

    def __init__(self, get_response: Callable[[WSGIRequest], DRFResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: WSGIRequest) -> DRFResponse:
        user_id: Optional[int] = self._get_user_id_from_jwt(request)
        lang: str = self._determine_language(request, user_id=user_id)
        tzname: str = self._determine_timezone(user_id=user_id)

        translation.activate(lang)
        request.LANGUAGE_CODE = lang

        timezone.activate(ZoneInfo(tzname))
        request.TIME_ZONE = tzname

        try:
            response: DRFResponse = self.get_response(request)
            response.headers.setdefault("Content-Language", lang)
            return response
        finally:
            timezone.deactivate()
            translation.deactivate()

    def _get_user_id_from_jwt(self, request: WSGIRequest) -> Optional[int]:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("JWT "):
            return None

        access_token: str = auth_header.strip().split(" ")[1]
        try:
            payload: dict[str, Any] = AccessToken(access_token)
            return payload.get("user_id")
        except TokenError:
            return None

    def _determine_language(self, request: WSGIRequest, user_id: Optional[int]) -> str:
        if user_id is not None:
            preferred: Optional[str] = PreferredLanguageCacheAccessor.get(user_id)
            normalized = self._normalize(preferred) if preferred else ""
            if normalized:
                return normalized

        query_lang: Optional[str] = request.GET.get("lang")
        normalized = self._normalize(query_lang) if query_lang else ""
        if normalized:
            return normalized

        accept_language: Optional[str] = request.headers.get("Accept-Language")
        normalized = (
            self._normalize_accept_language(accept_language) if accept_language else ""
        )
        if normalized:
            return normalized

        return ENGLISH_LANGUAGE_CODE

    def _determine_timezone(self, user_id: Optional[int]) -> str:
        if user_id is None:
            return "UTC"
        preferred_tz: Optional[str] = PreferredTimezoneCacheAccessor.get(user_id)
        if not preferred_tz:
            return "UTC"
        try:
            ZoneInfo(preferred_tz)
            return preferred_tz
        except Exception:
            return "UTC"

    def _normalize(self, lang: str) -> str:
        normalized = normalize_language_code(lang)
        return normalized if normalized in CustomUser.PREFERRED_LANGUAGES else ""

    def _normalize_accept_language(self, header_value: str) -> str:
        parts = [p.strip() for p in (header_value or "").split(",") if p.strip()]
        for part in parts:
            lang_part = part.split(";", 1)[0].strip()
            normalized = self._normalize(lang_part)
            if normalized:
                return normalized
        return ""

