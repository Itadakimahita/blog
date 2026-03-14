# Python modules
from typing import Any, Optional, Dict

# Django modules
from django.db.models import (
    EmailField,
    CharField,
    BooleanField,
    ForeignKey,
    SET_NULL,
    ManyToManyField,
    DateTimeField,
    ImageField,
)
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Project modules
from apps.abstracts.models import AbstractBaseModel, AbstractSoftDeletionModel
from apps.users.validators import validate_iana_timezone, validate_preferred_language


class CustomUserManager(BaseUserManager):
    """
    Custom user manager that extends Django's BaseUserManager.
    This manager provides methods for creating regular users and superusers.
    """
    
    def __obtain_user_instance(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        **kwargs: dict[str, Any],
    ) -> 'CustomUser':
        """Get user instance."""
        if not email:
            raise ValidationError(
                message=_("Email field is required."), code="email_empty"
            )
        if not first_name and not last_name:
            raise ValidationError(
                message=_("Full name field is required."), code="full_name_empty"
            )

        new_user: 'CustomUser' = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            password=password,
            **kwargs,
        )
        return new_user

    def create_user(self, email: str, first_name: str, last_name: str, password: str, **extra_fields: Dict[str, Any]) -> 'CustomUser':
        """
        Create and save a regular user with the given email, first name, last name, and password.
        """
        
        new_user = self.__obtain_user_instance(
            email=email, 
            first_name=first_name, 
            last_name=last_name, 
            password=password, 
            **extra_fields
        )
        new_user.set_password(password)
        new_user.save(using=self._db)
        return new_user
    
    def create_superuser(self, email: str, first_name: str, last_name: str, password: str, **extra_fields: Dict[str, Any]) -> 'CustomUser':
        """
        Create and save a superuser with the given email, first name, last name, and password.
        """
        
        new_user = self.__obtain_user_instance(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_staff=True,
            is_superuser=True,
            **extra_fields
        )
        new_user.set_password(password)
        new_user.save(using=self._db)
        return new_user


class CustomUser(AbstractBaseUser, PermissionsMixin, AbstractBaseModel, AbstractSoftDeletionModel):
    """
    Custom user model that extends Django's AbstractBaseUser and PermissionsMixin.
    This model includes:
    - `email`: A unique email field used for authentication.
    - `first_name`: A character field for the user's first name.
    - `last_name`: A character field for the user's last name.
    - `password`: A character field for the user's password, with validation.
    - `is_active`: A boolean field indicating if the user is active.
    - `is_staff`: A boolean field indicating if the user has staff privileges.
    - `date_joined`: A timestamp indicating when the user joined.
    - `avatar`: An optional image field for the user's avatar.
    """
    NAMES_LEN = 50
    EMAIL_LEN = 255
    PASSWORD_LEN = 128
    LANGUAGE_CODE_LEN = 8
    TIMEZONE_LEN = 64

    PREFERRED_LANGUAGES = ("en", "ru", "kk")

    email = EmailField(
        unique=True,
        max_length=EMAIL_LEN,
        verbose_name=_("email address"),
        help_text=_("Required. Enter a valid email address."),
    )
    first_name = CharField(
        max_length=NAMES_LEN,
        verbose_name=_("first name"),
        help_text=_("Required. Enter the user's first name."),
    )
    last_name = CharField(
        max_length=NAMES_LEN,
        verbose_name=_("last name"),
        help_text=_("Required. Enter the user's last name."),
    )
    password = CharField(
        max_length=PASSWORD_LEN,
        verbose_name=_("password"),
        help_text=_("Required. Enter the user's password."),
        validators=[validate_password],
    )
    is_active = BooleanField(
        default=True,
        verbose_name=_("active"),
        help_text=_(
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )
    is_staff = BooleanField(
        default=False,
        verbose_name=_("staff status"),
        help_text=_("Designates whether the user can log into this admin site."),
    )
    date_joined = DateTimeField(
        auto_now_add=True,
        verbose_name=_("date joined"),
        help_text=_("The date and time when the user account was created."),
    )
    avatar = ImageField(
        upload_to='static/avatars/',
        null=True,
        blank=True,
        verbose_name=_("avatar"),
        help_text=_("The user's avatar image."),
    )

    preferred_language = CharField(
        max_length=LANGUAGE_CODE_LEN,
        default="en",
        verbose_name=_("preferred language"),
        help_text=_("Choose your preferred language."),
        validators=[validate_preferred_language],
    )
    timezone = CharField(
        max_length=TIMEZONE_LEN,
        default="UTC",
        verbose_name=_("timezone"),
        help_text=_("Choose your timezone (IANA identifier)."),
        validators=[validate_iana_timezone],
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects = CustomUserManager()
    
    class Meta:
        """Meta class for CustomUser to specify verbose name and ordering."""
        
        verbose_name = 'Custom User'
        verbose_name_plural = 'Custom Users'
        ordering = ['-date_joined']
