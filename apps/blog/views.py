# Python modules
from typing import Any, List, Dict, Optional
import logging

# Django modules
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.db import transaction
from django.db.models import QuerySet, Count
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

# Django REST Framework
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request as DRFRequest
from rest_framework.response import Response as DRFResponse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_429_TOO_MANY_REQUESTS,
)
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

# Project modules
from apps.blog.models import Post, Comments as Comment, Tags, Category
from apps.blog.serializers import PostDetailSerializer, PostCreateSerializer, CommentDetailSerializer, CommentCreateSerializer
from apps.users.models import CustomUser
from apps.blog.enums.post_status import PostStatus
from apps.abstracts.rate_limit import is_rate_limited, too_many_requests_response
from apps.blog.cache import published_posts_list_cache_key
from apps.abstracts.serializers import ErrorDetailSerializer, ValidationErrorSerializer
from apps.notifications.tasks import process_new_comment


logger = logging.getLogger("blog")


class PostViewSet(GenericViewSet):
    permission_classes = [AllowAny]
    queryset = Post.objects.all()
    serializer_class = PostDetailSerializer

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action in {"create_post", "update_post"}:
            return PostCreateSerializer
        if action == "create_post_comment":
            return CommentCreateSerializer
        if action == "get_post_comments":
            return CommentDetailSerializer
        return PostDetailSerializer

    @extend_schema(
        summary="List published posts",
        description=(
            "Returns a cached list of published posts.\n\n"
            "Authentication: not required.\n"
            "Side effects:\n"
            "- Response is cached in Redis and varies by active language and timezone.\n"
            "- Cache is invalidated (via a version bump) whenever any post is created/updated/deleted.\n\n"
            "Language/timezone:\n"
            "- Timestamps are converted to the active request timezone and formatted according to the active request language.\n"
            "- Category names are returned in the active request language."
        ),
        tags=["Posts"],
        responses={
            HTTP_200_OK: PostDetailSerializer(many=True),
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
                        "title": "Hello",
                        "slug": "hello",
                        "body": "Post body",
                        "author": "author@example.com",
                        "category": {"slug": "news", "name": "News"},
                        "created_at": "2026-03-14T12:30:00Z",
                        "updated_at": "2026-03-14T12:30:00Z",
                        "created_at_display": "March 14, 2026, 12:30 p.m.",
                        "updated_at_display": "March 14, 2026, 12:30 p.m.",
                    }
                ],
            ),
            OpenApiExample(
                "404 Response Example",
                response_only=True,
                status_codes=[str(HTTP_404_NOT_FOUND)],
                value={"detail": "No posts found."},
            ),
        ],
    )
    @action(
        detail=False,
        methods=['get'],
        url_path='posts',
        url_name='posts-list',
    )
    def get_posts(self, request: DRFRequest, *args, **kwargs) -> DRFResponse:
        """
        Handle GET requests to retrieve a list of all posts.

        Parameters:
            request: DRFRequest
                The request object.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        
        Returns:
            DRFResponse
                A response indicating the result of the creation operation.
        """
        logger.debug("Get posts request received")
        try:
            # We use manual cache.get/cache.set instead of cache_page because
            # we must explicitly invalidate this cache on create/update events.
            language = getattr(request, "LANGUAGE_CODE", "en")
            timezone_name = getattr(request, "TIME_ZONE", "UTC")
            cache_key = published_posts_list_cache_key(
                language=language, timezone_name=timezone_name
            )

            cached_posts = cache.get(cache_key)
            if cached_posts is not None:
                logger.debug("Published posts served from cache")
                return DRFResponse(cached_posts, status=HTTP_200_OK)

            posts: QuerySet[Post] = Post.objects.filter(status=PostStatus.PUBLISHED).prefetch_related('tags', 'category')
            serializer: PostDetailSerializer = PostDetailSerializer(posts, many=True)
            if not serializer.data:
                logger.warning("No posts found")
                return DRFResponse({"detail": _("No posts found.")}, status=HTTP_404_NOT_FOUND)
            data: List[Dict[str, Any]] = serializer.data
            cache.set(cache_key, data, timeout=60)
            logger.info("Posts fetched successfully. Count=%s", len(data))
            return DRFResponse(data, status=HTTP_200_OK)
        except Exception:
            logger.exception("Unhandled exception while fetching posts")
            raise
    
    @extend_schema(
        summary="Create post",
        description=(
            "Creates a new post owned by the authenticated user.\n\n"
            "Authentication: required (JWT).\n"
            "Side effects:\n"
            "- Invalidates the cached published posts list (via a version bump).\n\n"
            "Language/timezone:\n"
            "- Validation errors and response strings are localized using the active request language.\n\n"
            "Rate limiting:\n"
            "- Returns 429 if the user exceeds the create-post rate limit."
        ),
        tags=["Posts"],
        request=PostCreateSerializer,
        responses={
            HTTP_201_CREATED: PostDetailSerializer,
            HTTP_400_BAD_REQUEST: ValidationErrorSerializer,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
            HTTP_429_TOO_MANY_REQUESTS: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"title": "Hello", "slug": "hello", "body": "Post body"},
            ),
            OpenApiExample(
                "201 Response Example",
                response_only=True,
                status_codes=[str(HTTP_201_CREATED)],
                value={
                    "id": 1,
                    "title": "Hello",
                    "slug": "hello",
                    "body": "Post body",
                    "author": "author@example.com",
                    "category": None,
                    "created_at": "2026-03-14T12:30:00Z",
                    "updated_at": "2026-03-14T12:30:00Z",
                    "created_at_display": "March 14, 2026, 12:30 p.m.",
                    "updated_at_display": "March 14, 2026, 12:30 p.m.",
                },
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
        methods=['post'],
        detail=False,
        url_path='posts',
        url_name='posts-create',
        permission_classes=[IsAuthenticated],
    )
    def create_post(self, request: DRFRequest, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> DRFResponse:
        """
        Handle POST requests to create a new post.
        Parameters:
            request: DRFRequest
                The request object containing the data for the new post.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        Returns:
            DRFResponse
                A response indicating the result of the creation operation.
        """
        user_id = getattr(request.user, "id", None)
        if is_rate_limited(
            key=f"rl:posts_create:user:{user_id}",
            limit=20,
            window_seconds=60,
        ):
            logger.warning("Rate limit exceeded for post creation user_id=%s", user_id)
            return too_many_requests_response()

        logger.info("Post creation attempt by user_id=%s", getattr(request.user, "id", None))
        try:
            serializer: PostCreateSerializer = PostCreateSerializer(data=request.data)
            if serializer.is_valid():
                post: Post = serializer.save(author=request.user)
                response_serializer: PostDetailSerializer = PostDetailSerializer(post)
                logger.info("Post created: %s", post.slug)
                return DRFResponse(response_serializer.data, status=HTTP_201_CREATED)
            logger.warning("Post creation failed validation errors=%s", serializer.errors)
            return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Post creation failed with exception")
            raise
    
    @extend_schema(
        summary="Get post by slug",
        description=(
            "Returns a single post by slug.\n\n"
            "Authentication: not required.\n"
            "Language/timezone:\n"
            "- Timestamps are converted to the active request timezone and formatted according to the active request language.\n"
            "- Category names are returned in the active request language."
        ),
        tags=["Posts"],
        responses={
            HTTP_200_OK: PostDetailSerializer,
            HTTP_404_NOT_FOUND: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={
                    "id": 1,
                    "title": "Hello",
                    "slug": "hello",
                    "body": "Post body",
                    "author": "author@example.com",
                    "category": {"slug": "news", "name": "News"},
                    "created_at": "2026-03-14T12:30:00Z",
                    "updated_at": "2026-03-14T12:30:00Z",
                    "created_at_display": "March 14, 2026, 12:30 p.m.",
                    "updated_at_display": "March 14, 2026, 12:30 p.m.",
                },
            )
        ],
    )
    @action(
        methods=['get'],
        detail=True,
        url_path='posts/(?P<slug>[^/.]+)',
        url_name='posts-detail',
    )
    def get_post(self, request: DRFRequest, slug: str, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> DRFResponse:
        """
        Handle GET requests to retrieve a specific post by its slug.
        Parameters:
            request: DRFRequest
                The request object.
            slug: str
                The slug of the post to retrieve.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        Returns:
            DRFResponse
                A response containing the details of the requested post or an error message if not found.
        """
        try:
            post: Post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            logger.warning("Requested post not found: %s", slug)
            return DRFResponse({"detail": _("Post not found.")}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while fetching post: %s", slug)
            raise
        
        serializer: PostDetailSerializer = PostDetailSerializer(post)
        logger.info("Post fetched: %s", slug)
        return DRFResponse(serializer.data, status=HTTP_200_OK)
    
    @extend_schema(
        summary="Update post",
        description=(
            "Partially updates a post by slug.\n\n"
            "Authentication: required (JWT).\n"
            "Side effects: invalidates the cached published posts list (via a version bump).\n"
            "Language/timezone: validation errors and response strings are localized using the active request language."
        ),
        tags=["Posts"],
        request=PostCreateSerializer,
        responses={
            HTTP_200_OK: PostDetailSerializer,
            HTTP_400_BAD_REQUEST: ValidationErrorSerializer,
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
            HTTP_404_NOT_FOUND: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"title": "Updated title"},
            ),
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                status_codes=[str(HTTP_200_OK)],
                value={
                    "id": 1,
                    "title": "Updated title",
                    "slug": "hello",
                    "body": "Post body",
                    "author": "author@example.com",
                    "category": None,
                    "created_at": "2026-03-14T12:30:00Z",
                    "updated_at": "2026-03-14T13:00:00Z",
                    "created_at_display": "March 14, 2026, 12:30 p.m.",
                    "updated_at_display": "March 14, 2026, 1:00 p.m.",
                },
            ),
        ],
    )
    @action(
        methods=['patch'],
        detail=True,
        url_path='posts',
        url_name='posts-update',
        permission_classes=[IsAuthenticated],
    )
    def update_post(self, request: DRFRequest, slug: str, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> DRFResponse:
        """
        Handle PATCH requests to update a specific post by its slug.
        Parameters:
            request: DRFRequest
                The request object containing the updated data for the post.
            slug: str
                The slug of the post to update.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        Returns:
            DRFResponse
                A response indicating the result of the update operation or an error message if not found.
        """
        logger.info("Post update attempt: %s by user_id=%s", slug, getattr(request.user, "id", None))
        try:
            post: Post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            logger.warning("Post update failed, not found: %s", slug)
            return DRFResponse({"detail": _("Post not found.")}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while loading post for update: %s", slug)
            raise
        
        serializer: PostCreateSerializer = PostCreateSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            updated_post: Post = serializer.save()
            response_serializer: PostDetailSerializer = PostDetailSerializer(updated_post)
            logger.info("Post updated: %s", updated_post.slug)
            return DRFResponse(response_serializer.data, status=HTTP_200_OK)
        
        logger.warning("Post update validation failed for slug=%s errors=%s", slug, serializer.errors)
        return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Delete post",
        description=(
            "Deletes a post by slug.\n\n"
            "Authentication: required (JWT).\n"
            "Side effects: invalidates the cached published posts list (via a version bump).\n"
            "Language/timezone: error strings are localized using the active request language."
        ),
        tags=["Posts"],
        responses={
            HTTP_204_NO_CONTENT: OpenApiResponse(description="Deleted."),
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
            HTTP_404_NOT_FOUND: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "404 Response Example",
                response_only=True,
                status_codes=[str(HTTP_404_NOT_FOUND)],
                value={"detail": "Post not found."},
            )
        ],
    )
    @action(
        methods=['delete'],
        detail=True,
        url_path='posts',
        url_name='posts-delete',
        permission_classes=[IsAuthenticated],
    )
    def delete_post(self, request: DRFRequest, slug: str, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> DRFResponse:
        """
        Handle DELETE requests to delete a specific post by its slug.
        Parameters:
            request: DRFRequest
                The request object.
            slug: str
                The slug of the post to delete.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        Returns:
            DRFResponse
                A response indicating the result of the deletion operation or an error message if not found.
        """
        logger.info("Post deletion attempt: %s by user_id=%s", slug, getattr(request.user, "id", None))
        try:
            post: Post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            logger.warning("Post deletion failed, not found: %s", slug)
            return DRFResponse({"detail": _("Post not found.")}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while loading post for deletion: %s", slug)
            raise
        
        post.delete()
        logger.info("Post deleted: %s", slug)
        return DRFResponse(status=HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="List comments for a post",
        description=(
            "Returns all comments for a given post slug.\n\n"
            "Authentication: not required.\n"
            "Side effects: none.\n"
            "Language/timezone: error strings are localized using the active request language."
        ),
        tags=["Comments"],
        responses={
            HTTP_200_OK: CommentDetailSerializer(many=True),
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
                        "post": 1,
                        "author": "author@example.com",
                        "body": "Nice post!",
                        "created_at": "2026-03-14T12:35:00Z",
                    }
                ],
            )
        ],
    )
    @action(
        methods=['get'],
        detail=False,
        url_path='posts/(?P<slug>[^/.]+)/comments',
        url_name='post-comments',
    )
    def get_post_comments(self, request: DRFRequest, slug: str, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> DRFResponse:
        """
        Handle GET requests to retrieve comments for a specific post by its slug.
        Parameters:
            request: DRFRequest
                The request object.
            slug: str
                The slug of the post whose comments are to be retrieved.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        Returns:
            DRFResponse
                A response containing the list of comments for the specified post or an error message if the post is not found.
        """
        try:
            post: Post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            logger.warning("Comments requested for missing post: %s", slug)
            return DRFResponse({"detail": _("Post not found.")}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while loading post comments: %s", slug)
            raise
        
        comments: QuerySet[Comment] = post.comments.all()
        if not comments.exists():
            logger.warning("No comments found for post: %s", slug)
            return DRFResponse({"detail": _("No comments found for this post.")}, status=HTTP_404_NOT_FOUND)
        serializer: CommentDetailSerializer = CommentDetailSerializer(comments, many=True)
        logger.info("Comments fetched for post: %s", slug)
        return DRFResponse(serializer.data, status=HTTP_200_OK)
    
    @extend_schema(
        summary="Create comment for a post",
        description=(
            "Creates a comment under a given post slug.\n\n"
            "Authentication: required (JWT).\n"
            "Side effects:\n"
            "- Broadcasts the new comment to the Channels group for this post.\n"
            "- Creates a notification for the post owner when another user comments.\n"
            "Language/timezone: validation errors and response strings are localized using the active request language."
        ),
        tags=["Comments"],
        request=CommentCreateSerializer,
        responses={
            HTTP_201_CREATED: CommentDetailSerializer,
            HTTP_400_BAD_REQUEST: OpenApiResponse(response=OpenApiTypes.OBJECT),
            HTTP_401_UNAUTHORIZED: ErrorDetailSerializer,
            HTTP_403_FORBIDDEN: ErrorDetailSerializer,
            HTTP_404_NOT_FOUND: ErrorDetailSerializer,
            HTTP_405_METHOD_NOT_ALLOWED: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request Example",
                request_only=True,
                value={"body": "Nice post!"},
            ),
            OpenApiExample(
                "201 Response Example",
                response_only=True,
                status_codes=[str(HTTP_201_CREATED)],
                value={
                    "id": 1,
                    "post": 1,
                    "author": "author@example.com",
                    "body": "Nice post!",
                    "created_at": "2026-03-14T12:35:00Z",
                },
            ),
        ],
    )
    @action(
        methods=['post'],
        detail=False,
        url_path='posts/(?P<slug>[^/.]+)/comments',
        url_name='post-comments',
        permission_classes=[IsAuthenticated],
    )
    def create_post_comment(self, request: DRFRequest, slug: str, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> DRFResponse:
        """
        Handle POST requests to create a new comment for a specific post by its slug.
        Parameters:
            request: DRFRequest
                The request object containing the data for the new comment.
            slug: str
                The slug of the post for which the comment is to be created.
            *args: list
                Additional positional arguments.
            **kwargs: dict
                Additional keyword arguments.
        Returns:
            DRFResponse
                A response indicating the result of the comment creation operation or an error message if the post is not found.
        """
        logger.info("Comment creation attempt on post: %s by user_id=%s", slug, getattr(request.user, "id", None))
        try:
            post: Post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            logger.warning("Comment creation failed, post not found: %s", slug)
            return DRFResponse({"detail": _("Post not found.")}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while loading post for comment creation: %s", slug)
            raise
        
        serializer: CommentCreateSerializer = CommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            comment: Comment = serializer.save(post=post, author=request.user)
            transaction.on_commit(lambda: process_new_comment.delay(comment.id))
            response_serializer: CommentDetailSerializer = CommentDetailSerializer(comment)
            logger.info("Comment created on post: %s", slug)
            return DRFResponse(response_serializer.data, status=HTTP_201_CREATED)
        logger.warning("Comment creation validation failed for post=%s errors=%s", slug, serializer.errors)
        return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
