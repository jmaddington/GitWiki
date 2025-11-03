"""
Celery tasks for git_service app.

Periodic tasks:
- periodic_github_pull: Pull from GitHub every 5 minutes
- cleanup_stale_branches_task: Clean up old branches daily
- full_static_rebuild_task: Rebuild all static files weekly

On-demand tasks:
- async_full_rebuild_task: Async full rebuild after incremental updates (safety net)
"""

import logging
from datetime import datetime

from celery import shared_task
from django.core.cache import cache

from .git_operations import get_repository

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def periodic_github_pull(self):
    """
    Periodic task: Pull from GitHub every 5 minutes.

    This task runs automatically via Celery Beat.
    It pulls the latest changes from the GitHub remote and
    regenerates static files if markdown files changed.

    Retries: 3 attempts with 60-second delay
    """
    try:
        logger.info('Starting periodic GitHub pull [TASK-PULL01]')

        repo = get_repository()
        result = repo.pull_from_github()

        # Update cache with last pull time
        cache.set('last_github_pull_time', datetime.now().isoformat(), None)

        if result.get('success'):
            files_changed = len(result.get('files_changed', []))
            logger.info(f'Periodic pull completed: {files_changed} files changed [TASK-PULL02]')
            return {
                'success': True,
                'files_changed': files_changed,
                'static_regenerated': result.get('static_regenerated', False)
            }
        else:
            logger.warning(f'Periodic pull had warnings: {result.get("message")} [TASK-PULL03]')
            return {
                'success': False,
                'message': result.get('message', 'Unknown error')
            }

    except Exception as e:
        error_msg = f'Periodic pull failed: {str(e)}'
        logger.error(f'{error_msg} [TASK-PULL04]')

        # Retry the task
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f'Periodic pull failed after 3 retries [TASK-PULL05]')
            return {
                'success': False,
                'message': error_msg,
                'max_retries_exceeded': True
            }


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def cleanup_stale_branches_task(self, age_days=7):
    """
    Periodic task: Clean up old branches daily.

    This task runs automatically via Celery Beat at 2 AM daily.
    It removes draft branches older than age_days that have
    inactive EditSessions.

    Args:
        age_days: Remove branches older than this (default: 7 days)

    Retries: 2 attempts with 120-second delay
    """
    try:
        logger.info(f'Starting branch cleanup (age_days={age_days}) [TASK-CLEANUP01]')

        repo = get_repository()
        result = repo.cleanup_stale_branches(age_days)

        # Update cache with last cleanup time
        cache.set('last_branch_cleanup_time', datetime.now().isoformat(), None)

        deleted = len(result['branches_deleted'])
        freed_mb = result['disk_space_freed_mb']

        logger.info(
            f'Branch cleanup completed: {deleted} branches deleted, '
            f'{freed_mb}MB freed [TASK-CLEANUP02]'
        )

        return {
            'success': True,
            'branches_deleted': deleted,
            'disk_space_freed_mb': freed_mb
        }

    except Exception as e:
        error_msg = f'Branch cleanup failed: {str(e)}'
        logger.error(f'{error_msg} [TASK-CLEANUP03]')

        # Retry the task
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f'Branch cleanup failed after 2 retries [TASK-CLEANUP04]')
            return {
                'success': False,
                'message': error_msg,
                'max_retries_exceeded': True
            }


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def full_static_rebuild_task(self):
    """
    Periodic task: Rebuild all static files weekly.

    This task runs automatically via Celery Beat on Sunday at 3 AM.
    It performs a complete regeneration of all static HTML files
    from the main branch and active draft branches.

    Retries: 2 attempts with 180-second delay
    """
    try:
        logger.info('Starting full static rebuild [TASK-REBUILD01]')

        repo = get_repository()
        result = repo.full_static_rebuild()

        # Update cache with last rebuild time
        cache.set('last_static_rebuild_time', datetime.now().isoformat(), None)

        branches = len(result['branches_regenerated'])
        total_files = result['total_files']
        execution_time = result['execution_time_ms']

        logger.info(
            f'Static rebuild completed: {branches} branches, '
            f'{total_files} files, {execution_time}ms [TASK-REBUILD02]'
        )

        return {
            'success': True,
            'branches_regenerated': branches,
            'total_files': total_files,
            'execution_time_ms': execution_time
        }

    except Exception as e:
        error_msg = f'Static rebuild failed: {str(e)}'
        logger.error(f'{error_msg} [TASK-REBUILD03]')

        # Retry the task
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f'Static rebuild failed after 2 retries [TASK-REBUILD04]')
            return {
                'success': False,
                'message': error_msg,
                'max_retries_exceeded': True
            }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def async_full_rebuild_task(self, branch_name='main'):
    """
    Async task: Full rebuild of static files for a specific branch.

    This task is queued after incremental rebuilds as a safety net
    to ensure eventual consistency. It regenerates all static files
    for the specified branch.

    Args:
        branch_name: Branch to rebuild (default: 'main')

    Retries: 3 attempts with 60-second delay
    """
    try:
        logger.info(f'Starting async full rebuild for branch {branch_name} [TASK-ASYNC-REBUILD01]')

        repo = get_repository()
        result = repo.write_branch_to_disk(branch_name)

        files_written = result.get('files_written', 0)
        markdown_files = result.get('markdown_files', 0)
        execution_time = result.get('execution_time_ms', 0)

        logger.info(
            f'Async rebuild completed for {branch_name}: {files_written} files, '
            f'{markdown_files} markdown, {execution_time}ms [TASK-ASYNC-REBUILD02]'
        )

        return {
            'success': True,
            'branch_name': branch_name,
            'files_written': files_written,
            'markdown_files': markdown_files,
            'execution_time_ms': execution_time
        }

    except Exception as e:
        error_msg = f'Async rebuild failed for {branch_name}: {str(e)}'
        logger.error(f'{error_msg} [TASK-ASYNC-REBUILD03]')

        # Retry the task
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f'Async rebuild failed after 3 retries for {branch_name} [TASK-ASYNC-REBUILD04]')
            return {
                'success': False,
                'branch_name': branch_name,
                'message': error_msg,
                'max_retries_exceeded': True
            }


@shared_task
def test_celery_task():
    """Test task to verify Celery is working."""
    logger.info('Test Celery task executed successfully [TASK-TEST01]')
    return {'status': 'success', 'message': 'Celery is working!'}
