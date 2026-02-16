# Python modules
from typing import Any, List, Dict, Optional

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
        users: QuerySet[CustomUser] = CustomUser.objects.all()
        if not users.exists():
            return DRFResponse({"detail": "No users found."}, status=HTTP_404_NOT_FOUND)
        serializer: UserDetailSerializer = UserDetailSerializer(users, many=True)
        return DRFResponse(serializer.data, status=HTTP_200_OK)

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
        serializer: UserRegisterSerializer = UserRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user: CustomUser = serializer.save()
        refresh: str = serializer.get_refresh(user)
        access: str = serializer.get_access(user)
        return DRFResponse({**serializer.data, "refresh": refresh, "access": access}, status=HTTP_201_CREATED)
    
    
