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
from apps.blog.models import Post, Comments as Comment, Tags, Category
from apps.blog.serializers import PostDetailSerializer, PostCreateSerializer, CommentDetailSerializer, CommentCreateSerializer
from apps.users.models import CustomUser


logger = logging.getLogger("blog")


class PostViewSet(ViewSet):
    """
    A viewset for viewing and editing post instances.
    """

    permission_classes = [AllowAny]

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
            posts: QuerySet[Post] = Post.objects.all().prefetch_related('tags', 'category')
            serializer: PostDetailSerializer = PostDetailSerializer(posts, many=True)
            if not serializer.data:
                logger.warning("No posts found")
                return DRFResponse({"detail": "No posts found."}, status=HTTP_404_NOT_FOUND)
            data: List[Dict[str, Any]] = serializer.data
            logger.info("Posts fetched successfully. Count=%s", len(data))
            return DRFResponse(data, status=HTTP_200_OK)
        except Exception:
            logger.exception("Unhandled exception while fetching posts")
            raise
    
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
        logger.info("Post creation attempt by user_id=%s", getattr(request.user, "id", None))
        try:
            data: Dict[str, Any] = request.data
            data["author"] = request.user.id
            serializer: PostCreateSerializer = PostCreateSerializer(data=data)
            if serializer.is_valid():
                post: Post = serializer.save()
                response_serializer: PostDetailSerializer = PostDetailSerializer(post)
                logger.info("Post created: %s", post.slug)
                return DRFResponse(response_serializer.data, status=HTTP_201_CREATED)
            logger.warning("Post creation failed validation errors=%s", serializer.errors)
            return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Post creation failed with exception")
            raise
    
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
            return DRFResponse({"detail": "Post not found."}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while fetching post: %s", slug)
            raise
        
        serializer: PostDetailSerializer = PostDetailSerializer(post)
        logger.info("Post fetched: %s", slug)
        return DRFResponse(serializer.data, status=HTTP_200_OK)
    
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
            return DRFResponse({"detail": "Post not found."}, status=HTTP_404_NOT_FOUND)
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
            return DRFResponse({"detail": "Post not found."}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while loading post for deletion: %s", slug)
            raise
        
        post.delete()
        logger.info("Post deleted: %s", slug)
        return DRFResponse(status=HTTP_204_NO_CONTENT)
    
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
            return DRFResponse({"detail": "Post not found."}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while loading post comments: %s", slug)
            raise
        
        comments: QuerySet[Comment] = post.comments.all()
        if not comments.exists():
            logger.warning("No comments found for post: %s", slug)
            return DRFResponse({"detail": "No comments found for this post."}, status=HTTP_404_NOT_FOUND)
        serializer: CommentDetailSerializer = CommentDetailSerializer(comments, many=True)
        logger.info("Comments fetched for post: %s", slug)
        return DRFResponse(serializer.data, status=HTTP_200_OK)
    
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
            return DRFResponse({"detail": "Post not found."}, status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Error while loading post for comment creation: %s", slug)
            raise
        
        data = {**request.data, "post": post.id, "author": request.user.id}
        serializer: CommentCreateSerializer = CommentCreateSerializer(data=data)
        if serializer.is_valid():
            comment: Comment = serializer.save(post=post)
            response_serializer: CommentDetailSerializer = CommentDetailSerializer(comment)
            logger.info("Comment created on post: %s", slug)
            return DRFResponse(response_serializer.data, status=HTTP_201_CREATED)
        logger.warning("Comment creation validation failed for post=%s errors=%s", slug, serializer.errors)
        return DRFResponse(serializer.errors, status=HTTP_400_BAD_REQUEST)
