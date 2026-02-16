from typing import Any, Dict

# Django REST Framework modules
from rest_framework.serializers import ModelSerializer, SerializerMethodField, EmailField, CharField
from rest_framework_simplejwt.tokens import RefreshToken

# Project modules
from apps.users.models import CustomUser

        
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
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar']
        
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
            "access",
            "refresh",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
        }
    
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
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=validated_data["password"],
        )
        validated_data["access"] = self.get_access(user)
        validated_data["refresh"] = self.get_refresh(user)
        return user
