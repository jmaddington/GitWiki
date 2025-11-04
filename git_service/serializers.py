"""
Serializers for Git Service API.
"""

from rest_framework import serializers


class CreateBranchSerializer(serializers.Serializer):
    """Serializer for create branch request."""
    # No fields needed - uses authenticated user from request


class CommitChangesSerializer(serializers.Serializer):
    """Serializer for commit changes request."""
    branch_name = serializers.CharField(max_length=255)
    file_path = serializers.CharField(max_length=1024)
    content = serializers.CharField()
    commit_message = serializers.CharField(max_length=500)
    # user_info removed - uses authenticated user from request via get_user_info_for_commit()


class PublishDraftSerializer(serializers.Serializer):
    """Serializer for publish draft request."""
    branch_name = serializers.CharField(max_length=255)
    auto_push = serializers.BooleanField(default=True)


class GetFileSerializer(serializers.Serializer):
    """Serializer for get file request."""
    file_path = serializers.CharField(max_length=1024)
    branch = serializers.CharField(max_length=255, default='main')
