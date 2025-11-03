# Generated migration to clean up duplicate active sessions
# AIDEV-NOTE: duplicate-cleanup; Prepares database for unique constraint by removing duplicates

from django.db import migrations
import logging

logger = logging.getLogger(__name__)


def cleanup_duplicate_active_sessions(apps, schema_editor):
    """
    Find and clean up duplicate active sessions before adding unique constraint.

    Strategy: Keep the most recently modified session, mark others as inactive.
    """
    EditSession = apps.get_model('editor', 'EditSession')

    # Find all user+file combinations with multiple active sessions
    from django.db.models import Count

    duplicates = (EditSession.objects
                  .filter(is_active=True)
                  .values('user', 'file_path')
                  .annotate(count=Count('id'))
                  .filter(count__gt=1))

    total_duplicates = duplicates.count()
    if total_duplicates == 0:
        logger.info('No duplicate active sessions found [MIGRATION-CLEANUP01]')
        return

    logger.info(f'Found {total_duplicates} user+file combinations with duplicate active sessions [MIGRATION-CLEANUP02]')

    deactivated_count = 0
    for dup in duplicates:
        # Get all active sessions for this user+file, ordered by most recent first
        sessions = (EditSession.objects
                    .filter(user_id=dup['user'],
                           file_path=dup['file_path'],
                           is_active=True)
                    .order_by('-last_modified'))

        session_count = sessions.count()
        logger.info(
            f'User {dup["user"]} has {session_count} active sessions for {dup["file_path"]} [MIGRATION-CLEANUP03]'
        )

        # Keep the first (most recent), mark others as inactive
        for session in sessions[1:]:
            session.is_active = False
            session.save(update_fields=['is_active'])
            deactivated_count += 1
            logger.info(
                f'Deactivated duplicate session {session.id} (branch: {session.branch_name}) [MIGRATION-CLEANUP04]'
            )

    logger.info(f'Cleanup complete: Deactivated {deactivated_count} duplicate sessions [MIGRATION-CLEANUP05]')


def reverse_cleanup(apps, schema_editor):
    """
    No reverse operation - we cannot restore which sessions should have been active.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('editor', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cleanup_duplicate_active_sessions, reverse_cleanup),
    ]
