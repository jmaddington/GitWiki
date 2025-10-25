from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)


class Configuration(models.Model):
    """
    Stores application-wide configuration settings.

    AIDEV-NOTE: config-model; Provides get/set helpers for type-safe config access
    """
    key = models.CharField(max_length=255, unique=True, db_index=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"
        ordering = ['key']

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_config(cls, key, default=None):
        """Get configuration value by key."""
        try:
            config = cls.objects.get(key=key)
            return config.value
        except cls.DoesNotExist:
            logger.warning(f'Configuration key not found: {key} [CONFIG-GET01]')
            return default

    @classmethod
    def set_config(cls, key, value, description=""):
        """Set configuration value by key."""
        try:
            config, created = cls.objects.update_or_create(
                key=key,
                defaults={'value': value, 'description': description}
            )
            action = "created" if created else "updated"
            logger.info(f'Configuration {action}: {key} [CONFIG-SET01]')
            return config
        except Exception as e:
            logger.error(f'Failed to set configuration {key}: {str(e)} [CONFIG-SET02]')
            raise

    @classmethod
    def initialize_defaults(cls):
        """Initialize default configuration values."""
        defaults = {
            'github_remote_url': {'value': '', 'desc': 'GitHub repository URL'},
            'github_ssh_key_path': {'value': '', 'desc': 'Path to SSH private key'},
            'auto_push_enabled': {'value': True, 'desc': 'Automatically push to GitHub after merge'},
            'permission_level': {'value': 'read_only_public', 'desc': 'Access control level: open, read_only_public, private'},
            'branch_prefix_draft': {'value': 'draft', 'desc': 'Prefix for draft branches'},
            'max_image_size_mb': {'value': 10, 'desc': 'Maximum image upload size in MB'},
            'supported_image_formats': {'value': ['png', 'jpg', 'jpeg', 'webp'], 'desc': 'Allowed image formats'},
            'webhook_secret': {'value': '', 'desc': 'GitHub webhook secret for verification'},
        }

        for key, config in defaults.items():
            if not cls.objects.filter(key=key).exists():
                cls.set_config(key, config['value'], config['desc'])

        logger.info('Default configurations initialized [CONFIG-INIT01]')


class GitOperation(models.Model):
    """
    Audit log for all Git operations.

    AIDEV-NOTE: audit-trail; Complete history of all git operations for debugging
    """
    OPERATION_TYPES = [
        ('create_branch', 'Create Branch'),
        ('commit', 'Commit'),
        ('merge', 'Merge'),
        ('push', 'Push'),
        ('pull', 'Pull'),
        ('delete_branch', 'Delete Branch'),
        ('static_gen', 'Static Generation'),
        ('conflict_detect', 'Conflict Detection'),
        ('conflict_resolve', 'Conflict Resolution'),
    ]

    operation_type = models.CharField(max_length=50, choices=OPERATION_TYPES, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    branch_name = models.CharField(max_length=255, blank=True, db_index=True)
    file_path = models.CharField(max_length=1024, blank=True)
    request_parameters = models.JSONField(default=dict)
    response_code = models.IntegerField(default=200)
    success = models.BooleanField(default=True, db_index=True)
    git_output = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    execution_time_ms = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Git Operation"
        verbose_name_plural = "Git Operations"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'operation_type']),
            models.Index(fields=['success', '-timestamp']),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        user_str = f" by {self.user.username}" if self.user else ""
        return f"{status} {self.operation_type}{user_str} at {self.timestamp}"

    @classmethod
    def log_operation(cls, operation_type, user=None, branch_name='', file_path='',
                     request_params=None, response_code=200, success=True,
                     git_output='', error_message='', execution_time_ms=0):
        """
        Create a new operation log entry.

        Returns the created GitOperation instance.
        """
        try:
            operation = cls.objects.create(
                operation_type=operation_type,
                user=user,
                branch_name=branch_name,
                file_path=file_path,
                request_parameters=request_params or {},
                response_code=response_code,
                success=success,
                git_output=git_output,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
            )

            log_level = logging.INFO if success else logging.ERROR
            log_msg = f'{operation_type} operation {"succeeded" if success else "failed"}'
            if branch_name:
                log_msg += f' on branch {branch_name}'
            logger.log(log_level, f'{log_msg} [GITOP-LOG01]')

            return operation
        except Exception as e:
            logger.error(f'Failed to log git operation: {str(e)} [GITOP-LOG02]')
            # Don't raise - logging failure shouldn't break operations
            return None
