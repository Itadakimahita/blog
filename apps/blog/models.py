# Python modules
from typing import Any, Optional, Dict

# Django modules
from django.db.models import (
    CharField,
    BooleanField,
    ForeignKey,
    SET_NULL,
    CASCADE,
    ManyToManyField,
    SlugField,
    TextField,
    TextChoices,
)
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# Project modules
from apps.abstracts.models import AbstractBaseModel, AbstractSoftDeletionModel, AbstractSlugBaseModel
from apps.users.models import CustomUser
from apps.blog.enums.post_status import PostStatus


class Category(AbstractBaseModel, AbstractSlugBaseModel):
    """
    Model representing a category for blog posts.
    The model includes:
    - `name`: A unique character field for the category name.
    - `slug`: A unique slug field for URL-friendly representation of the category name.
    """
    NAME_MAX_LENGTH = 100
    
    name = CharField(
        max_length=NAME_MAX_LENGTH, 
        unique=True,
        verbose_name="Category Name",
        help_text="The name of the category. Must be unique.",
    )

    def __repr__(self) -> str:
        """
        Return a string representation of the Category instance, including its name, slug, and associated users. 
        This is useful for debugging and logging purposes.
        """
        return f"Category(name={self.name}, slug={self.slug})"

    def __str__(self) -> str:
        """Return the string representation of the Category instance, which is its name."""
        return self.name
    
class Tags(AbstractBaseModel, AbstractSlugBaseModel):
    """
    Model representing a tag for blog posts.
    The model includes:
    - `name`: A unique character field for the tag name.
    - `slug`: A unique slug field for URL-friendly representation of the tag name.
    """
    NAME_MAX_LENGTH = 50
    
    name = CharField(
        max_length=NAME_MAX_LENGTH, 
        unique=True,
        verbose_name="Tag Name",
        help_text="The name of the tag. Must be unique.",
    )

    def __repr__(self) -> str:
        """
        Return a string representation of the Tag instance, including its name and slug. 
        This is useful for debugging and logging purposes.
        """
        return f"Tag(name={self.name}, slug={self.slug})"

    def __str__(self) -> str:
        """Return the string representation of the Tag instance, which is its name."""
        return self.name


class Post(AbstractBaseModel, AbstractSlugBaseModel, AbstractSoftDeletionModel):
    """
    Model representing a blog post.
    The model includes:
    - `title`: A character field for the post title.
    - `slug`: A unique slug field for URL-friendly representation of the post title.
    - `body`: A text field for the post content.
    - `status`: A character field for the post status, with choices defined in the Post Status.
    - `author`: A foreign key to the CustomUser model, representing the author of the post.
    - `category`: A foreign key to the Category model, representing the category of the post.
    - `tags`: A many-to-many field to the Tags model, representing the tags associated with the post.
    """
    TITLE_MAX_LENGTH = 200
    STATUS_MAX_LENGTH = 20
    
    title = CharField(
        max_length=TITLE_MAX_LENGTH,
        verbose_name="Post Title",
        help_text="The title of the blog post.",
    )
    body = TextField(
        verbose_name="Post Content",
        help_text="The content of the blog post.",
    )
    status = CharField(
        max_length=STATUS_MAX_LENGTH,
        choices=PostStatus.choices,
        default=PostStatus.DRAFT,
        verbose_name="Post Status",
        help_text="The status of the blog post. Can be 'draft', 'published', or 'archived'.",
    )
    
    author = ForeignKey(
        CustomUser, 
        on_delete=CASCADE,
        related_name='posts',
        verbose_name="Author",
        help_text="The author of the blog post. If the author is deleted, the post will also be deleted.",
    )
    category = ForeignKey(
        to=Category, 
        on_delete=SET_NULL, 
        null=True, 
        blank=True,
        related_name='posts',
        verbose_name="Category",
        help_text="The category associated with this blog post. Can be null if the category is deleted.",
    )
    tags = ManyToManyField(
        to=Tags, 
        blank=True,
        related_name='posts',
        verbose_name="Tags",
        help_text="The tags associated with this blog post. A post can have multiple tags.",
    )
    
    def __repr__(self):
        """Return a string representation of the Post instance, including its title, slug, status, and author."""
        return super().__repr__() + f"Post(title={self.title}, slug={self.slug}, status={self.status}, author={self.author.username})"
    
    def __str__(self):
        """Return the string representation of the Post instance, which is its title."""
        return self.title
    

class Comments(AbstractBaseModel):
    """
    Model representing a comment on a blog post.
    The model includes:
    - `body`: A text field for the comment content.
    - `author`: A foreign key to the CustomUser model, representing the author of the
    - `post`: A foreign key to the Post model, representing the blog post that this comment is associated with.
    """
    body = TextField(
        verbose_name="Comment Content",
        help_text="The content of the comment.",
    )
    author = ForeignKey(
        to=CustomUser, 
        on_delete=CASCADE,
        related_name='comments',
        verbose_name="Author",
        help_text="The author of the comment. If the author is deleted, the comment will also be deleted.",
    )
    post = ForeignKey(
        to=Post, 
        on_delete=CASCADE, 
        related_name='comments',
        verbose_name="Post",
        help_text="The blog post that this comment is associated with. If the post is deleted, the comment will also be deleted.",
    )
    
    def __repr__(self):
        """Return a string representation of the Comment instance, including its body, author, and associated post."""
        return super().__repr__() + f"Comment(body={self.body}, author={self.author.username}, post={self.post.title})"
    
    def __str__(self):
        """Return the string representation of the Comment instance, which is its body."""
        return self.body