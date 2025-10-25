"""
Serializers for Git Service API.
"""

from rest_framework import serializers


class CreateBranchSerializer(serializers.Serializer):
    """Serializer for create branch request."""
    user_id = serializers.IntegerField(min_value=1)


class CommitChangesSerializer(serializers.Serializer):
    """Serializer for commit changes request."""
    branch_name = serializers.CharField(max_length=255)
    file_path = serializers.CharField(max_length=1024)
    content = serializers.CharField()
    commit_message = serializers.CharField(max_length=500)
    user_info = serializers.DictField(child=serializers.CharField())

    def validate_user_info(self, value):
        """Validate user_info has required fields."""
        if 'name' not in value or 'email' not in value:
            raise serializers.ValidationError("user_info must contain 'name' and 'email'")
        return value


class PublishDraftSerializer(serializers.Serializer):
    """Serializer for publish draft request."""
    branch_name = serializers.CharField(max_length=255)
    auto_push = serializers.BooleanField(default=True)


class GetFileSerializer(serializers.Serializer):
    """Serializer for get file request."""
    file_path = serializers.CharField(max_length=1024)
    branch = serializers.CharField(max_length=255, default='main')
