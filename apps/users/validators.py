from __future__ import annotations

from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


SUPPORTED_LANGUAGE_CODES = ("en", "ru", "kk")
LANGUAGE_CODE_ALIASES = {
    "kz": "kk",
    "kaz": "kk",
}


def normalize_language_code(lang: str) -> str:
    lang = (lang or "").strip().lower()
    if not lang:
        return ""
    lang = lang.split("-", 1)[0]
    return LANGUAGE_CODE_ALIASES.get(lang, lang)


def validate_preferred_language(value: str) -> None:
    normalized = normalize_language_code(value)
    if normalized not in SUPPORTED_LANGUAGE_CODES:
        raise ValidationError(
            _("Unsupported language. Supported: en, ru, kk."),
            code="unsupported_language",
        )


def validate_iana_timezone(value: str) -> None:
    tz = (value or "").strip()
    if not tz:
        raise ValidationError(_("Timezone is required."), code="timezone_required")
    try:
        ZoneInfo(tz)
    except Exception:
        raise ValidationError(
            _(
                "Invalid timezone. Use a valid IANA identifier (e.g. 'UTC' or 'Asia/Almaty')."
            ),
            code="invalid_timezone",
        )
