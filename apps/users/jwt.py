import logging

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


logger = logging.getLogger("users")


class LoggingTokenObtainPairSerializer(TokenObtainPairSerializer):
    """A custom serializer that extends the TokenObtainPairSerializer to include logging of login attempts."""
    def validate(self, attrs: dict) -> dict:
        """Validate the user credentials and log the login attempt."""
        email = attrs.get(self.username_field)
        logger.info("Login attempt for email: %s", email)
        try:
            data = super().validate(attrs)
            user = getattr(self, "user", None)
            user_email = getattr(user, "email", email)
            logger.info("Login success for email: %s", user_email)
            return data
        except Exception:
            logger.warning("Login failed for email: %s", email)
            logger.exception("Login exception for email: %s", email)
            raise
