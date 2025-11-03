# Generated migration to add unique constraint for active sessions
# AIDEV-NOTE: unique-constraint; Prevents duplicate active sessions at database level

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('editor', '0002_cleanup_duplicate_sessions'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='editsession',
            constraint=models.UniqueConstraint(
                fields=['user', 'file_path'],
                condition=models.Q(is_active=True),
                name='unique_active_session_per_user_file',
                violation_error_message='An active session already exists for this user and file'
            ),
        ),
    ]
