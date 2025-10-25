"""
Views for git_service app.

Handles GitHub webhook, sync management, and GitHub settings.
"""

import hmac
import hashlib
import json
import logging
from datetime import datetime

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.cache import cache

from .git_operations import get_repository
from .models import Configuration
from .utils import test_ssh_connection, validate_remote_url

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def github_webhook_handler(request):
    """
    Handle incoming GitHub webhooks.

    AIDEV-NOTE: webhook-handler; Rate-limited to 1 pull/minute

    Process:
    1. Verify webhook secret (if configured)
    2. Rate limit check (max 1/min)
    3. Trigger pull_from_github()
    4. Return status

    Rate Limiting:
    - Store last pull timestamp in cache
    - Return cached status if within 1 minute
    - Log rate-limited requests

    Returns:
        HTTP 200: {"action": "pulled", "changes": true}
        HTTP 429: {"action": "rate_limited", "retry_after": 45}
        HTTP 401: {"action": "unauthorized"}
        HTTP 400: {"action": "invalid_payload"}
    """
    try:
        # Get webhook secret from configuration
        webhook_secret = Configuration.get_config('webhook_secret')

        # Verify signature if webhook secret is configured
        if webhook_secret:
            signature = request.headers.get('X-Hub-Signature-256', '')

            if not signature:
                logger.warning('Webhook received without signature [WEBHOOK-01]')
                return JsonResponse({
                    'action': 'unauthorized',
                    'message': 'Missing webhook signature'
                }, status=401)

            # Calculate expected signature
            expected_signature = 'sha256=' + hmac.new(
                webhook_secret.encode('utf-8'),
                request.body,
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning('Webhook signature verification failed [WEBHOOK-02]')
                return JsonResponse({
                    'action': 'unauthorized',
                    'message': 'Invalid webhook signature'
                }, status=401)

        # Parse payload
        try:
            payload = json.loads(request.body)
            event_type = request.headers.get('X-GitHub-Event', 'unknown')

            logger.info(f'Webhook received: {event_type} [WEBHOOK-03]')
        except json.JSONDecodeError:
            logger.error('Invalid JSON payload in webhook [WEBHOOK-04]')
            return JsonResponse({
                'action': 'invalid_payload',
                'message': 'Invalid JSON'
            }, status=400)

        # Rate limiting: Only pull once per minute
        cache_key = 'last_webhook_pull_time'
        last_pull_time = cache.get(cache_key)

        if last_pull_time:
            # Calculate time since last pull
            time_diff = (datetime.now() - datetime.fromisoformat(last_pull_time)).total_seconds()

            if time_diff < 60:
                retry_after = int(60 - time_diff)
                logger.info(f'Webhook rate limited (retry after {retry_after}s) [WEBHOOK-05]')
                return JsonResponse({
                    'action': 'rate_limited',
                    'message': f'Rate limited. Try again in {retry_after} seconds.',
                    'retry_after': retry_after
                }, status=429)

        # Trigger pull from GitHub
        repo = get_repository()
        result = repo.pull_from_github()

        # Update last pull time
        cache.set(cache_key, datetime.now().isoformat(), 120)  # Cache for 2 minutes

        logger.info(f'Webhook pull completed: {result} [WEBHOOK-06]')

        return JsonResponse({
            'action': 'pulled',
            'success': result.get('success', False),
            'changes_detected': result.get('changes_detected', False),
            'files_changed': len(result.get('files_changed', [])),
            'message': result.get('message', 'Pull completed')
        }, status=200)

    except Exception as e:
        logger.error(f'Webhook handler error: {str(e)} [WEBHOOK-07]')
        return JsonResponse({
            'action': 'error',
            'message': str(e)
        }, status=500)


def is_staff_user(user):
    """Check if user is staff."""
    return user.is_staff


@login_required
@user_passes_test(is_staff_user)
def sync_management(request):
    """
    Admin page for GitHub sync management.

    Features:
    - Manual "Sync Now" button
    - Manual "Rebuild Static" button
    - Manual "Cleanup Branches" button
    - Show last sync time
    - Show sync status/errors
    - Show periodic task status
    """
    # Get last sync info from cache
    last_pull = cache.get('last_github_pull_time')
    last_rebuild = cache.get('last_static_rebuild_time')
    last_cleanup = cache.get('last_branch_cleanup_time')

    # Handle manual actions
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'sync_now':
            try:
                repo = get_repository()
                result = repo.pull_from_github()

                if result.get('success'):
                    files_changed = len(result.get('files_changed', []))
                    messages.success(request, f"Successfully synced from GitHub. {files_changed} files changed.")
                    logger.info(f'Manual sync completed: {files_changed} files [SYNC-01]')
                else:
                    messages.warning(request, f"Sync completed with warnings: {result.get('message', 'Unknown error')}")
                    logger.warning(f'Manual sync had warnings: {result.get("message")} [SYNC-02]')

                # Update cache
                cache.set('last_github_pull_time', datetime.now().isoformat(), None)

            except Exception as e:
                messages.error(request, f"Sync failed: {str(e)}")
                logger.error(f'Manual sync failed: {str(e)} [SYNC-03]')

        elif action == 'rebuild_static':
            try:
                # Import here to avoid circular imports
                from .tasks import full_static_rebuild_task

                # Queue task (or run directly if Celery not available)
                try:
                    result = full_static_rebuild_task.delay()
                    messages.info(request, f"Static rebuild started. Task ID: {result.id}")
                    logger.info(f'Static rebuild task queued: {result.id} [SYNC-04]')
                except Exception:
                    # Celery not available, run directly
                    repo = get_repository()
                    result = repo.full_static_rebuild()
                    messages.success(request, f"Static rebuild completed. {result['branches_regenerated']} branches regenerated.")
                    logger.info(f'Static rebuild completed: {result} [SYNC-05]')
                    cache.set('last_static_rebuild_time', datetime.now().isoformat(), None)

            except Exception as e:
                messages.error(request, f"Rebuild failed: {str(e)}")
                logger.error(f'Static rebuild failed: {str(e)} [SYNC-06]')

        elif action == 'cleanup_branches':
            try:
                # Import here to avoid circular imports
                from .tasks import cleanup_stale_branches_task

                # Get age_days from form (default 7)
                age_days = int(request.POST.get('age_days', 7))

                # Queue task (or run directly if Celery not available)
                try:
                    result = cleanup_stale_branches_task.delay(age_days)
                    messages.info(request, f"Branch cleanup started. Task ID: {result.id}")
                    logger.info(f'Branch cleanup task queued: {result.id} [SYNC-07]')
                except Exception:
                    # Celery not available, run directly
                    repo = get_repository()
                    result = repo.cleanup_stale_branches(age_days)
                    deleted = len(result['branches_deleted'])
                    freed_mb = result['disk_space_freed_mb']
                    messages.success(request, f"Cleanup completed. {deleted} branches deleted, {freed_mb}MB freed.")
                    logger.info(f'Branch cleanup completed: {result} [SYNC-08]')
                    cache.set('last_branch_cleanup_time', datetime.now().isoformat(), None)

            except Exception as e:
                messages.error(request, f"Cleanup failed: {str(e)}")
                logger.error(f'Branch cleanup failed: {str(e)} [SYNC-09]')

    context = {
        'last_pull': last_pull,
        'last_rebuild': last_rebuild,
        'last_cleanup': last_cleanup,
        'github_remote_url': Configuration.get_config('github_remote_url'),
        'auto_push_enabled': Configuration.get_config('auto_push_enabled', False),
    }

    return render(request, 'git_service/sync.html', context)


@login_required
@user_passes_test(is_staff_user)
def github_settings(request):
    """
    GitHub configuration page.

    Features:
    - GitHub remote URL input
    - SSH key path input
    - Auto-push toggle
    - Webhook secret
    - Test SSH connection button
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_settings':
            # Save GitHub settings
            remote_url = request.POST.get('remote_url', '').strip()
            ssh_key_path = request.POST.get('ssh_key_path', '').strip()
            auto_push = request.POST.get('auto_push') == 'on'
            webhook_secret = request.POST.get('webhook_secret', '').strip()

            # Validate remote URL
            if remote_url and not validate_remote_url(remote_url):
                messages.error(request, "Invalid remote URL format")
            else:
                # Save configuration
                Configuration.set_config('github_remote_url', remote_url)
                Configuration.set_config('github_ssh_key_path', ssh_key_path)
                Configuration.set_config('auto_push_enabled', auto_push)
                Configuration.set_config('webhook_secret', webhook_secret)

                messages.success(request, "Settings saved successfully")
                logger.info('GitHub settings updated [SETTINGS-01]')

        elif action == 'test_ssh':
            # Test SSH connection
            remote_url = request.POST.get('remote_url', '').strip()
            ssh_key_path = request.POST.get('ssh_key_path', '').strip() or None

            if not remote_url:
                messages.error(request, "Please enter a remote URL first")
            else:
                result = test_ssh_connection(remote_url, ssh_key_path)

                if result['success']:
                    messages.success(request, f"SSH connection successful to {result['host']}")
                    logger.info(f'SSH test successful: {result["host"]} [SETTINGS-02]')
                else:
                    messages.error(request, f"SSH connection failed: {result['message']}")
                    logger.warning(f'SSH test failed: {result["message"]} [SETTINGS-03]')

    # Load current settings
    settings_data = {
        'remote_url': Configuration.get_config('github_remote_url', ''),
        'ssh_key_path': Configuration.get_config('github_ssh_key_path', ''),
        'auto_push': Configuration.get_config('auto_push_enabled', False),
        'webhook_secret': Configuration.get_config('webhook_secret', ''),
    }

    return render(request, 'git_service/github_settings.html', settings_data)


def is_admin(user):
    """Check if user is admin/staff."""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET", "POST"])
def configuration_page(request):
    """
    Configuration management page for administrators.

    AIDEV-NOTE: config-page; Manage wiki settings and permissions

    Features:
    - Permission level configuration (open, read_only_public, private)
    - Wiki branding (title, description)
    - File upload limits
    - Branch cleanup thresholds
    - Image format settings

    Permission Modes:
    - open: No auth required (fully public wiki)
    - read_only_public: Public read, auth for edit
    - private: Auth required for all access
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_config':
            try:
                # Permission level
                permission_level = request.POST.get('permission_level', 'read_only_public')
                if permission_level in ['open', 'read_only_public', 'private']:
                    Configuration.set_config('permission_level', permission_level)
                    logger.info(f'Permission level updated to: {permission_level} [CONFIG-01]')
                else:
                    messages.error(request, f"Invalid permission level: {permission_level}")
                    logger.warning(f'Invalid permission level attempted: {permission_level} [CONFIG-02]')

                # Wiki settings
                wiki_title = request.POST.get('wiki_title', 'GitWiki').strip()
                Configuration.set_config('wiki_title', wiki_title)

                wiki_description = request.POST.get('wiki_description', '').strip()
                Configuration.set_config('wiki_description', wiki_description)

                # File upload limits
                try:
                    max_image_size = int(request.POST.get('max_image_size_mb', 10))
                    if 1 <= max_image_size <= 100:
                        Configuration.set_config('max_image_size_mb', max_image_size)
                    else:
                        messages.warning(request, "Image size must be between 1-100 MB. Using default: 10 MB")
                except ValueError:
                    messages.warning(request, "Invalid image size. Using default: 10 MB")

                # Branch cleanup threshold
                try:
                    cleanup_days = int(request.POST.get('branch_cleanup_days', 7))
                    if 1 <= cleanup_days <= 365:
                        Configuration.set_config('branch_cleanup_days', cleanup_days)
                    else:
                        messages.warning(request, "Cleanup days must be between 1-365. Using default: 7 days")
                except ValueError:
                    messages.warning(request, "Invalid cleanup days. Using default: 7 days")

                # Image formats
                image_formats = request.POST.get('supported_image_formats', 'png,jpg,jpeg,webp').strip().lower()
                Configuration.set_config('supported_image_formats', image_formats)

                messages.success(request, "Configuration saved successfully!")
                logger.info('Wiki configuration updated successfully [CONFIG-03]')

            except Exception as e:
                messages.error(request, f"Failed to save configuration: {str(e)}")
                logger.error(f'Configuration save failed: {str(e)} [CONFIG-04]')

    # Load current configuration
    config_data = {
        'permission_level': Configuration.get_config('permission_level', 'read_only_public'),
        'wiki_title': Configuration.get_config('wiki_title', 'GitWiki'),
        'wiki_description': Configuration.get_config('wiki_description', 'A distributed, Git-backed wiki system'),
        'max_image_size_mb': Configuration.get_config('max_image_size_mb', 10),
        'branch_cleanup_days': Configuration.get_config('branch_cleanup_days', 7),
        'supported_image_formats': Configuration.get_config('supported_image_formats', 'png,jpg,jpeg,webp'),
    }

    return render(request, 'git_service/configuration.html', config_data)
