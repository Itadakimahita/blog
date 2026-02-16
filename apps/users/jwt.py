import logging

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


logger = logging.getLogger("users")


class LoggingTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
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
