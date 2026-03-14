# apps/common/serializers.py
from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    """Serializer for error details."""
    detail = serializers.CharField()


class ValidationErrorSerializer(serializers.Serializer):
    """Error serializer for validation errors."""
    errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )


class MessageSerializer(serializers.Serializer):
    """Serializer for simple message responses."""
    detail = serializers.CharField()


class BlogStatsSerializer(serializers.Serializer):
    total_posts = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    total_users = serializers.IntegerField()


class StatsResponseSerializer(serializers.Serializer):
    blog = BlogStatsSerializer()
    exchange_rates = serializers.DictField(child=serializers.FloatField())
    current_time = serializers.CharField()
