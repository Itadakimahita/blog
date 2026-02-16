# Python modules
from typing import Any, List, Dict, Optional
import logging

# Django modules
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.db.models import QuerySet, Count

# Django REST Framework
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request as DRFRequest
from rest_framework.response import Response as DRFResponse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from rest_framework.decorators import action

# Project modules
from apps.users.models import CustomUser
from apps.users.serializers import UserDetailSerializer, UserRegisterSerializer
from apps.abstracts.rate_limit import (
    client_ip_from_request,
    is_rate_limited,
    too_many_requests_response,
)


logger = logging.getLogger("users")


class UserViewSet(ViewSet):
    """
    A viewset for managing users in the application.
    """
    permission_classes = [AllowAny,]

    def list(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> DRFResponse:
        """
        Return a list of all users.

        Parameters:
            request: HttpRequest
                The request object.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        
        Returns:
            DRFResponse: 
                A response object containing the list of users and the HTTP status code.
        """
        logger.debug("List users request received")
        try:
            users: QuerySet[CustomUser] = CustomUser.objects.all()
            if not users.exists():
                logger.warning("List users requested but no users found")
                return DRFResponse({"detail": "No users found."}, status=HTTP_404_NOT_FOUND)
            serializer: UserDetailSerializer = UserDetailSerializer(users, many=True)
            logger.info("List users success. Count=%s", users.count())
            return DRFResponse(serializer.data, status=HTTP_200_OK)
        except Exception:
            logger.exception("Unhandled exception while listing users")
            raise

    @action(
        methods=["post"],
        detail=False,
        permission_classes=[AllowAny,],
        url_name="register",
        url_path="register",
    )
    def register(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: Dict[str, Any]) -> DRFResponse:
        """
        Register a new user.

        Parameters:
            request: HttpRequest
                The request object containing the user data.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        
        Returns:
            DRFResponse: 
                A response object containing the created user data and the HTTP status code.
        """
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
            return DRFResponse({**serializer.data, "refresh": refresh, "access": access}, status=HTTP_201_CREATED)
        except Exception:
            logger.exception("Registration failed with exception for email: %s", email)
            raise
    
    
