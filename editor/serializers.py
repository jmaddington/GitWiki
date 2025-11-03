"""
API serializers for Editor Service.

AIDEV-NOTE: editor-serializers; Validation for all editor API endpoints
"""

from rest_framework import serializers
from django.contrib.auth.models import User


class StartEditSerializer(serializers.Serializer):
    """Serializer for starting an edit session."""
    user_id = serializers.IntegerField(required=True, min_value=1)
    file_path = serializers.CharField(required=True, max_length=1024)

    def validate_file_path(self, value):
        """Validate file path is safe and ends with .md."""
        # AIDEV-NOTE: path-validation; Prevent directory traversal attacks
        if '..' in value or value.startswith('/'):
            raise serializers.ValidationError("Invalid file path: no absolute paths or parent directory references allowed")

        if not value.endswith('.md'):
            raise serializers.ValidationError("File must be a markdown file (.md)")

        return value


class SaveDraftSerializer(serializers.Serializer):
    """Serializer for saving draft content (client-side)."""
    session_id = serializers.IntegerField(required=True, min_value=1)
    content = serializers.CharField(required=True, allow_blank=True)


class CommitDraftSerializer(serializers.Serializer):
    """Serializer for committing draft to Git."""
    session_id = serializers.IntegerField(required=True, min_value=1)
    content = serializers.CharField(required=True, allow_blank=True)
    commit_message = serializers.CharField(required=True, max_length=500)

    def validate_commit_message(self, value):
        """Validate commit message is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Commit message cannot be empty")
        return value.strip()


class PublishEditSerializer(serializers.Serializer):
    """Serializer for publishing edit to main branch."""
    session_id = serializers.IntegerField(required=True, min_value=1)
    content = serializers.CharField(required=False, allow_blank=True)  # Optional: commit before publish
    commit_message = serializers.CharField(required=False, allow_blank=True, max_length=500)
    auto_push = serializers.BooleanField(default=True)


class ValidateMarkdownSerializer(serializers.Serializer):
    """Serializer for markdown validation."""
    content = serializers.CharField(required=True, allow_blank=True)


class UploadImageSerializer(serializers.Serializer):
    """Serializer for image upload."""
    session_id = serializers.IntegerField(required=True, min_value=1)
    image = serializers.ImageField(required=True)
    alt_text = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")

    def validate_image(self, value):
        """Validate image file type and size."""
        from git_service.models import Configuration

        # Get allowed formats and max size from configuration
        allowed_formats = Configuration.get_config('supported_image_formats', ['png', 'jpg', 'jpeg', 'webp'])
        max_size_mb = Configuration.get_config('max_image_size_mb', 10)
        max_size_bytes = max_size_mb * 1024 * 1024

        # Check file extension
        file_ext = value.name.split('.')[-1].lower()
        if file_ext not in allowed_formats:
            raise serializers.ValidationError(
                f"Invalid image format. Allowed formats: {', '.join(allowed_formats)}"
            )

        # Check file size
        if value.size > max_size_bytes:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size: {max_size_mb}MB"
            )

        return value
