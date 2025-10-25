"""
Celery configuration for GitWiki.

This module configures Celery for background tasks including:
- Periodic GitHub pulls (every 5 minutes)
- Daily branch cleanup
- Weekly static rebuild
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('gitwiki')

# Load configuration from Django settings (namespace='CELERY')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Configure periodic task schedule
app.conf.beat_schedule = {
    'pull-from-github-every-5-min': {
        'task': 'git_service.tasks.periodic_github_pull',
        'schedule': 300.0,  # 5 minutes in seconds
        'options': {'expires': 60},  # Task expires after 60 seconds
    },
    'cleanup-stale-branches-daily': {
        'task': 'git_service.tasks.cleanup_stale_branches_task',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'args': (7,),  # age_days parameter
        'options': {'expires': 3600},  # Task expires after 1 hour
    },
    'full-static-rebuild-weekly': {
        'task': 'git_service.tasks.full_static_rebuild_task',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        'options': {'expires': 7200},  # Task expires after 2 hours
    },
}

# Additional Celery settings
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
