"""
API serializers for Editor Service.

AIDEV-NOTE: editor-serializers; Validation for all editor API endpoints
"""

from rest_framework import serializers


class StartEditSerializer(serializers.Serializer):
    """Serializer for starting an edit session."""
    user_id = serializers.IntegerField(min_value=1)
    file_path = serializers.CharField(max_length=1024)

    def validate_file_path(self, value):
        """Validate file path doesn't contain malicious patterns."""
        # AIDEV-NOTE: path-security; Prevent directory traversal attacks
        if '..' in value or value.startswith('/'):
            raise serializers.ValidationError("Invalid file path")
        if not value.endswith('.md'):
            raise serializers.ValidationError("Only markdown files (.md) are supported")
        return value


class ValidateMarkdownSerializer(serializers.Serializer):
    """Serializer for markdown validation."""
    content = serializers.CharField(allow_blank=True)


class CommitDraftSerializer(serializers.Serializer):
    """Serializer for committing draft changes."""
    session_id = serializers.IntegerField(min_value=1)
    content = serializers.CharField()
    commit_message = serializers.CharField(max_length=500)


class PublishEditSerializer(serializers.Serializer):
    """Serializer for publishing draft to main."""
    session_id = serializers.IntegerField(min_value=1)
    auto_push = serializers.BooleanField(default=True)


class UploadImageSerializer(serializers.Serializer):
    """Serializer for image uploads."""
    session_id = serializers.IntegerField(min_value=1)
    image = serializers.ImageField()
    alt_text = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_image(self, value):
        """Validate image type and size."""
        from git_service.models import Configuration

        # Get max size from configuration (default 10MB)
        max_size_mb = int(Configuration.get_config('max_image_size_mb', '10'))
        max_size_bytes = max_size_mb * 1024 * 1024

        if value.size > max_size_bytes:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size is {max_size_mb}MB"
            )

        # Get supported formats
        supported_formats_str = Configuration.get_config(
            'supported_image_formats',
            '["image/png", "image/jpeg", "image/webp"]'
        )
        import json
        supported_formats = json.loads(supported_formats_str)

        if value.content_type not in supported_formats:
            raise serializers.ValidationError(
                f"Unsupported image format. Supported formats: PNG, JPEG, WebP"
            )

        return value


class DiscardDraftSerializer(serializers.Serializer):
    """Serializer for discarding a draft."""
    session_id = serializers.IntegerField(min_value=1)
