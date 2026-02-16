from typing import Any, Dict

# Django REST Framework modules
from rest_framework.serializers import ModelSerializer, SerializerMethodField, EmailField, CharField
from rest_framework_simplejwt.tokens import RefreshToken

# Project modules
from apps.blog.models import Post, Comments, Tags, Category
from apps.users.models import CustomUser


class PostDetailSerializer(ModelSerializer):
    """
    Serializer for the Post model, which includes the following fields:
    - `id`: The unique identifier of the post.
    - `title`: The title of the post.
    - `content`: The content of the post.
    - `author`: The username of the author of the post.
    - `created_at`: The date and time when the post was created.
    """
    author = CharField(source="author.email", read_only=True)
    
    class Meta:
        """Meta class for PostDetailSerializer to specify the model and fields to be serialized."""
        model = Post
        fields = ['id', 'title', 'slug', 'body', 'author', 'created_at']
    

class PostCreateSerializer(ModelSerializer):
    """
    Serializer for creating a new post, which includes the following fields:
    - `title`: The title of the post.
    - `content`: The content of the post.
    - `author`: The ID of the author of the post.
    """
    
    class Meta:
        """Meta class for PostCreateSerializer to specify the model and fields to be serialized."""
        model = Post
        fields = ['title', 'slug', 'body', 'author']
    
    def create(self, validated_data: Dict[str, Any]) -> Post:
        """Create a new post instance."""
        post = Post.objects.create(**validated_data)
        return post
        
class CommentDetailSerializer(ModelSerializer):
    """
    Serializer for the Comment model, which includes the following fields:
    - `id`: The unique identifier of the comment.
    - `post`: The ID of the post that the comment belongs to.
    - `author`: The username of the author of the comment.
    - `content`: The content of the comment.
    - `created_at`: The date and time when the comment was created.
    """
    author = CharField(source="author.email", read_only=True)
    
    class Meta:
        """Meta class for CommentSerializer to specify the model and fields to be serialized."""
        model = Comments
        fields = ['id', 'post', 'author', 'content', 'created_at']
        

class CommentCreateSerializer(ModelSerializer):
    """
    Serializer for creating a new comment, which includes the following fields:
    - `post`: The ID of the post that the comment belongs to.
    - `author`: The ID of the author of the comment.
    - `content`: The content of the comment.
    """
    
    class Meta:
        """Meta class for CommentCreateSerializer to specify the model and fields to be serialized."""
        model = Comments
        fields = ['post', 'author', 'content']
    
    def create(self, validated_data: Dict[str, Any]) -> Comments:
        """Create a new comment instance."""
        comment = Comments.objects.create(**validated_data)
        return comment
    
