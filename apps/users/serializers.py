from typing import Any, Dict
import logging

# Django REST Framework modules
from rest_framework.serializers import (
    ModelSerializer,
    SerializerMethodField,
    ValidationError,
)
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from django.db import transaction

# Project modules
from apps.users.models import CustomUser
from apps.users.caches import PreferredLanguageCacheAccessor, PreferredTimezoneCacheAccessor
from apps.users.tasks import send_welcome_email
from apps.users.validators import normalize_language_code, SUPPORTED_LANGUAGE_CODES


logger = logging.getLogger("users")

        
class UserDetailSerializer(ModelSerializer):
    """
    Serializer for retrieving detailed information about a user.
    This serializer includes the following fields:
    - `id`: The unique identifier of the user.
    - `username`: The username of the user.
    - `email`: The email address of the user.
    - `first_name`: The first name of the user.
    - `last_name`: The last name of the user.
    - `avatar`: The avatar image of the user.
    """
    
    class Meta:
        """Meta class for UserDetailSerializer to specify the model and fields to be serialized."""
        model = CustomUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "preferred_language",
            "timezone",
        ]
        
class UserRegisterSerializer(ModelSerializer):
    """
    Serializer for registering a new user.
    This serializer includes the following fields:
    - `username`: The username of the user.
    - `email`: The email address of the user.
    - `password`: The password for the user account.
    - `first_name`: The first name of the user.
    - `last_name`: The last name of the user.
    """
    refresh = SerializerMethodField(read_only=True)
    access = SerializerMethodField(read_only=True)
    
    class Meta:
        """Meta class for UserRegisterSerializer to specify the model and fields to be serialized."""
        model = CustomUser
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "preferred_language",
            "timezone",
            "access",
            "refresh",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_preferred_language(self, value: str) -> str:
        normalized = normalize_language_code(value)
        if normalized not in SUPPORTED_LANGUAGE_CODES:
            raise ValidationError(_("Unsupported language. Supported: en, ru, kk."))
        return normalized
    
    def get_refresh(self, obj: CustomUser) -> str:
        """Generate refresh token for the user."""
        refresh = RefreshToken.for_user(obj)
        return str(refresh)
    
    def get_access(self, obj: CustomUser) -> str:
        """Generate access token for the user."""
        refresh = RefreshToken.for_user(obj)
        return str(refresh.access_token)
    
    def create(self, validated_data: Dict[str, Any]) -> CustomUser:
        """Create a new user with hashed password."""
        email = validated_data.get("email")
        logger.debug("Creating user record for email: %s", email)
        try:
            user = CustomUser.objects.create_user(
                email=validated_data["email"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                password=validated_data["password"],
                preferred_language=validated_data.get("preferred_language", "en"),
                timezone=validated_data.get("timezone", "UTC"),
            )
            PreferredLanguageCacheAccessor.set(
                user_id=user.id, preferred_language=user.preferred_language
            )
            PreferredTimezoneCacheAccessor.set(user_id=user.id, timezone_name=user.timezone)
            transaction.on_commit(
                lambda: send_welcome_email.delay(user_id=user.id, language=user.preferred_language)
            )
            validated_data["access"] = self.get_access(user)
            validated_data["refresh"] = self.get_refresh(user)
            logger.info("User created in serializer: %s", user.email)
            return user
        except Exception:
            logger.exception("User creation failed in serializer for email: %s", email)
            raise


class UserPreferredLanguageSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["preferred_language"]

    def validate_preferred_language(self, value: str) -> str:
        normalized = normalize_language_code(value)
        if normalized not in SUPPORTED_LANGUAGE_CODES:
            raise ValidationError(_("Unsupported language. Supported: en, ru, kk."))
        return normalized


class UserTimezoneSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["timezone"]

    def validate_timezone(self, value: str) -> str:
        return (value or "").strip()
