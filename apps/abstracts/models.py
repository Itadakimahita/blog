from typing import Any, Dict, Optional

from django.db import models
from django.utils import timezone


class AbstractBaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.
    This model includes:
    - `created_at`: A timestamp indicating when the record was created.
    - `updated_at`: A timestamp indicating when the record was last updated.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        
        
class AbstractSoftDeletionModel(models.Model):
    """
    Abstract base model that provides a soft delete field for all models.
    This model includes:
    - `deleted_at`: A timestamp indicating when the record was deleted.
    - `is_deleted`: A boolean field indicating if the record is deleted.
    """
    
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        """Meta class for AbstractSoftDeletionModel to specify that this is an abstract model."""
        
        abstract = True
    
    def delete(self, using: Optional[str] = None, keep_parents: bool = False) -> None:
        """
        Override the delete method to perform a soft delete by setting `is_deleted` to True.
        """
        
        self.deleted_at = timezone.now()
        self.is_deleted = True
        self.save(update_fields=['deleted_at', 'is_deleted'])
        

class AbstractSlugBaseModel(models.Model):
    """
    Abstract base model that provides a slug field for all models.
    This model includes:
    - `slug`: A unique slug field for URL-friendly representation of the model instance.
    """
    
    slug = models.SlugField(
        unique=True,
        verbose_name="URL Slug",
        help_text="A URL-friendly version of the model instance name.",
        )

    class Meta:
        """Meta class for AbstractSlugBaseModel to specify that this is an abstract model."""
        
        abstract = True