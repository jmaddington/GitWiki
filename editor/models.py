from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class EditSession(models.Model):
    """
    Tracks active editing sessions before publishing.

    AIDEV-NOTE: session-tracking; Maps users to their draft branches
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='edit_sessions')
    file_path = models.CharField(max_length=1024)
    branch_name = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Edit Session"
        verbose_name_plural = "Edit Sessions"
        ordering = ['-last_modified']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['-last_modified']),
        ]
        # AIDEV-NOTE: unique-constraint; Prevents duplicate active sessions (fixes #22)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'file_path'],
                condition=models.Q(is_active=True),
                name='unique_active_session_per_user_file',
                violation_error_message='An active session already exists for this user and file'
            )
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{status} - {self.user.username}: {self.file_path} ({self.branch_name})"

    def mark_inactive(self):
        """Mark this edit session as inactive."""
        self.is_active = False
        self.save(update_fields=['is_active', 'last_modified'])
        logger.info(f'Edit session marked inactive: {self.branch_name} [EDITSESS-INACTIVE01]')

    def touch(self):
        """Update the last_modified timestamp."""
        self.last_modified = timezone.now()
        self.save(update_fields=['last_modified'])

    @classmethod
    def get_active_sessions(cls, user=None):
        """
        Get all active edit sessions, optionally filtered by user.

        Args:
            user: Optional User instance to filter by

        Returns:
            QuerySet of active EditSession instances
        """
        queryset = cls.objects.filter(is_active=True)
        if user:
            queryset = queryset.filter(user=user)
        return queryset

    @classmethod
    def get_user_session_for_file(cls, user, file_path):
        """
        Get active session for a specific user and file.

        With unique constraint in place (see #22), MultipleObjectsReturned should never occur.
        If it does, it indicates a critical database integrity issue.

        Returns:
            EditSession instance or None
        """
        try:
            return cls.objects.get(user=user, file_path=file_path, is_active=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # CRITICAL: This should never happen with unique constraint in place
            logger.error(
                f'CRITICAL: Unique constraint violated! Multiple active sessions for '
                f'{user.username}:{file_path} - database integrity compromised [EDITSESS-CONSTRAINT-FAIL01]'
            )
            # Fallback: return most recent to prevent complete failure
            return cls.objects.filter(
                user=user,
                file_path=file_path,
                is_active=True
            ).order_by('-last_modified').first()
