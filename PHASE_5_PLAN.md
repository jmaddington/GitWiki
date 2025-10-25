# Phase 5 Implementation Plan - GitHub Integration

**Date:** October 25, 2025
**Status:** Ready to Begin
**Estimated Duration:** 8-10 days
**Priority:** High

---

## Executive Summary

Phase 5 implements GitHub synchronization capabilities, enabling GitWiki to:
- Pull changes from GitHub remote repository
- Push local changes to GitHub
- Respond to GitHub webhooks
- Run periodic background tasks (pull, cleanup, rebuild)
- Manage stale branch cleanup
- Trigger full static rebuilds

**Prerequisites (All Met):**
- ✅ Phases 1-4 complete
- ✅ Atomic git operations working
- ✅ Conflict resolution functional
- ✅ Comprehensive logging in place

---

## Phase 5 Goals

### Primary Objectives
1. **Bidirectional GitHub Sync** - Pull from and push to GitHub
2. **Webhook Integration** - Respond to GitHub push events
3. **Background Tasks** - Celery-based periodic jobs
4. **Branch Cleanup** - Remove stale draft branches
5. **Static Rebuild** - Full regeneration capability

### Success Criteria
- [ ] Can pull latest changes from GitHub
- [ ] Can push local commits to GitHub
- [ ] Webhook triggers sync (with rate limiting)
- [ ] Periodic tasks running reliably
- [ ] Stale branches cleaned up automatically
- [ ] All operations logged with grepable codes

---

## Implementation Plan

### Week 1: Core GitHub Operations (Days 1-5)

#### Day 1-2: SSH Configuration & Pull Implementation

**Tasks:**
1. **SSH Key Management**
   - Add SSH validation utility
   - Add connection testing
   - Document SSH setup process

2. **Implement `pull_from_github()`**
```python
def pull_from_github(self) -> Dict:
    """
    Pull latest changes from GitHub remote.

    AIDEV-NOTE: github-pull; Handles conflicts during pull gracefully

    Process:
    1. Git fetch from remote
    2. Check for diverged branches
    3. Git pull (merge remote changes)
    4. Detect changed files
    5. Trigger static regeneration if needed
    6. Log operation

    Returns:
        {
            "success": true,
            "changes_detected": true,
            "files_changed": ["docs/page1.md", "docs/page2.md"],
            "static_regenerated": true,
            "conflicts": []  # if merge conflicts during pull
        }
    """
```

**Implementation Notes:**
- Use GitPython's `origin.pull()` method
- Handle merge conflicts gracefully
- Regenerate static files only if changes detected
- Log with codes: GITOPS-PULL01 through GITOPS-PULL05
- Add AIDEV-NOTE: github-pull

**Testing:**
- [ ] Test successful pull with changes
- [ ] Test pull with no changes
- [ ] Test pull with local uncommitted changes
- [ ] Test pull with conflicts
- [ ] Test SSH connection failures

---

#### Day 3: Push Implementation

**Implement `push_to_github()`**
```python
def push_to_github(self, branch: str = "main") -> Dict:
    """
    Push local changes to GitHub remote.

    AIDEV-NOTE: github-push; Only pushes if local is ahead

    Args:
        branch: Branch name to push (default: main)

    Process:
    1. Check for unpushed commits
    2. Verify SSH connection
    3. Git push to remote
    4. Handle push failures
    5. Log operation

    Returns:
        {
            "success": true,
            "branch": "main",
            "commits_pushed": 3,
            "remote_updated": true
        }

    Error Codes:
    - 409: Remote has changes, need to pull first
    - 401: SSH authentication failed
    - 502: GitHub connection failed
    """
```

**Implementation Notes:**
- Check if local branch is ahead before pushing
- Use `repo.remotes.origin.push()`
- Handle "diverged branches" error (HTTP 409)
- Log with codes: GITOPS-PUSH01 through GITOPS-PUSH05
- Add AIDEV-NOTE: github-push

**Testing:**
- [ ] Test push with commits
- [ ] Test push with no commits
- [ ] Test push with diverged branches
- [ ] Test SSH authentication failures
- [ ] Test network errors

---

#### Day 4: Webhook Handler

**Create Webhook Endpoint**
```python
# git_service/views.py

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
    """
```

**Implementation Notes:**
- POST endpoint at `/api/git/webhook/`
- Verify GitHub signature if webhook secret configured
- Use Django cache for rate limiting (60 second window)
- Log with codes: WEBHOOK-01 through WEBHOOK-05
- Add AIDEV-NOTE: webhook-handler

**Testing:**
- [ ] Test webhook with valid signature
- [ ] Test rate limiting (multiple calls)
- [ ] Test invalid signatures
- [ ] Test malformed requests

---

#### Day 5: Cleanup Operations

**1. Implement `cleanup_stale_branches()`**
```python
def cleanup_stale_branches(self, age_days: int = 7) -> Dict:
    """
    Remove old draft branches and their static files.

    AIDEV-NOTE: branch-cleanup; Only removes inactive sessions

    Args:
        age_days: Remove branches older than this (default: 7)

    Process:
    1. List all draft branches
    2. Check last commit date
    3. Check if EditSession is still active
    4. Delete old, inactive branches
    5. Remove associated static files
    6. Log operation

    Returns:
        {
            "success": true,
            "branches_deleted": ["draft-123-abc", "draft-456-def"],
            "branches_kept": ["draft-789-ghi"],  # still active
            "disk_space_freed_mb": 150
        }
    """
```

**2. Implement `full_static_rebuild()`**
```python
def full_static_rebuild(self) -> Dict:
    """
    Complete regeneration of all static files.

    AIDEV-NOTE: static-rebuild; Atomic operation, old files kept until complete

    Process:
    1. Generate to temp directory
    2. Regenerate main branch
    3. Regenerate active draft branches
    4. Verify integrity
    5. Atomic swap
    6. Log operation

    Returns:
        {
            "success": true,
            "branches_regenerated": ["main", "draft-123-abc"],
            "total_files": 150,
            "execution_time_ms": 5000
        }
    """
```

**Implementation Notes:**
- cleanup_stale_branches() checks EditSession.is_active
- Log with codes: GITOPS-CLEANUP01 through GITOPS-CLEANUP05
- Log with codes: GITOPS-REBUILD01 through GITOPS-REBUILD05
- Add AIDEV-NOTEs

**Testing:**
- [ ] Test cleanup with old branches
- [ ] Test cleanup preserves active sessions
- [ ] Test full rebuild
- [ ] Test rebuild failure recovery

---

### Week 2: Celery Integration & UI (Days 6-10)

#### Day 6-7: Celery Setup

**1. Install Dependencies**
```bash
pip install celery redis django-celery-beat
```

**2. Configure Celery**
```python
# config/celery.py

from celery import Celery
from celery.schedules import crontab

app = Celery('gitwiki')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    'pull-from-github-every-5-min': {
        'task': 'git_service.tasks.periodic_github_pull',
        'schedule': 300.0,  # 5 minutes
    },
    'cleanup-stale-branches-daily': {
        'task': 'git_service.tasks.cleanup_stale_branches',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'full-static-rebuild-weekly': {
        'task': 'git_service.tasks.full_static_rebuild',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
    },
}
```

**3. Create Tasks**
```python
# git_service/tasks.py

from celery import shared_task
from .git_operations import get_repository
import logging

logger = logging.getLogger(__name__)

@shared_task
def periodic_github_pull():
    """Periodic task: Pull from GitHub every 5 minutes."""
    try:
        repo = get_repository()
        result = repo.pull_from_github()
        logger.info(f'Periodic pull completed: {result} [TASK-PULL01]')
        return result
    except Exception as e:
        logger.error(f'Periodic pull failed: {str(e)} [TASK-PULL02]')
        raise

@shared_task
def cleanup_stale_branches_task(age_days=7):
    """Periodic task: Clean up old branches daily."""
    try:
        repo = get_repository()
        result = repo.cleanup_stale_branches(age_days)
        logger.info(f'Branch cleanup completed: {result} [TASK-CLEANUP01]')
        return result
    except Exception as e:
        logger.error(f'Branch cleanup failed: {str(e)} [TASK-CLEANUP02]')
        raise

@shared_task
def full_static_rebuild_task():
    """Periodic task: Rebuild all static files weekly."""
    try:
        repo = get_repository()
        result = repo.full_static_rebuild()
        logger.info(f'Static rebuild completed: {result} [TASK-REBUILD01]')
        return result
    except Exception as e:
        logger.error(f'Static rebuild failed: {str(e)} [TASK-REBUILD02]')
        raise
```

**4. Update Settings**
```python
# config/settings.py

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Django Cache Configuration (for rate limiting)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

**Testing:**
- [ ] Celery worker starts successfully
- [ ] Celery beat scheduler starts
- [ ] Periodic tasks execute
- [ ] Task failures logged properly

---

#### Day 8: Admin UI

**Create Sync Management Page**
```python
# git_service/views.py

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
    if not request.user.is_staff:
        return HttpResponseForbidden("Admin access required")

    # Get last sync info
    last_pull = cache.get('last_github_pull_time')
    last_rebuild = cache.get('last_static_rebuild_time')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'sync_now':
            repo = get_repository()
            result = repo.pull_from_github()
            messages.success(request, f"Synced: {result['files_changed']} files changed")

        elif action == 'rebuild_static':
            result = full_static_rebuild_task.delay()
            messages.info(request, f"Rebuild started: Task ID {result.id}")

        elif action == 'cleanup_branches':
            result = cleanup_stale_branches_task.delay()
            messages.info(request, f"Cleanup started: Task ID {result.id}")

    return render(request, 'git_service/sync.html', {
        'last_pull': last_pull,
        'last_rebuild': last_rebuild,
    })
```

**Template: git_service/templates/sync.html**
```html
{% extends "base.html" %}

{% block content %}
<h1>GitHub Sync Management</h1>

<div class="card mb-3">
    <div class="card-header">Manual Actions</div>
    <div class="card-body">
        <form method="post">
            {% csrf_token %}
            <button type="submit" name="action" value="sync_now" class="btn btn-primary">
                <i class="fas fa-sync"></i> Sync Now
            </button>
            <button type="submit" name="action" value="rebuild_static" class="btn btn-warning">
                <i class="fas fa-hammer"></i> Rebuild Static Files
            </button>
            <button type="submit" name="action" value="cleanup_branches" class="btn btn-danger">
                <i class="fas fa-trash"></i> Cleanup Stale Branches
            </button>
        </form>
    </div>
</div>

<div class="card">
    <div class="card-header">Status</div>
    <div class="card-body">
        <p><strong>Last Pull:</strong> {{ last_pull|default:"Never" }}</p>
        <p><strong>Last Rebuild:</strong> {{ last_rebuild|default:"Never" }}</p>
        <p><strong>Periodic Tasks:</strong> Active (every 5 min / daily / weekly)</p>
    </div>
</div>
{% endblock %}
```

---

#### Day 9: Configuration UI

**Enhance Settings Page**
```python
# git_service/views.py

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
        # Save settings
        Configuration.set_config('github_remote_url', request.POST.get('remote_url'))
        Configuration.set_config('github_ssh_key_path', request.POST.get('ssh_key_path'))
        Configuration.set_config('auto_push_enabled', request.POST.get('auto_push') == 'on')
        Configuration.set_config('webhook_secret', request.POST.get('webhook_secret'))

        messages.success(request, "Settings saved successfully")

    # Load current settings
    settings = {
        'remote_url': Configuration.get_config('github_remote_url'),
        'ssh_key_path': Configuration.get_config('github_ssh_key_path'),
        'auto_push': Configuration.get_config('auto_push_enabled'),
        'webhook_secret': Configuration.get_config('webhook_secret'),
    }

    return render(request, 'git_service/github_settings.html', settings)
```

**Add SSH Test Utility**
```python
# git_service/utils.py

def test_ssh_connection(remote_url: str, ssh_key_path: str) -> Dict:
    """
    Test SSH connection to GitHub.

    Returns:
        {
            "success": true/false,
            "message": "Connection successful" or error details
        }
    """
    import subprocess

    try:
        # Extract host from git URL
        # git@github.com:user/repo.git -> github.com
        host = remote_url.split('@')[1].split(':')[0]

        result = subprocess.run(
            ['ssh', '-i', ssh_key_path, '-T', f'git@{host}'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # GitHub returns 1 even on successful auth
        if 'successfully authenticated' in result.stderr.lower():
            return {"success": True, "message": "SSH connection successful"}
        else:
            return {"success": False, "message": result.stderr}

    except Exception as e:
        return {"success": False, "message": str(e)}
```

---

#### Day 10: Testing & Documentation

**1. Integration Tests**
```python
# git_service/tests.py

class GitHubIntegrationTests(TestCase):
    def test_pull_from_github_with_changes(self):
        """Test pulling changes from remote."""
        # Mock GitHub remote with changes
        # Assert changes detected
        # Assert static regenerated

    def test_push_to_github_success(self):
        """Test pushing commits to GitHub."""
        # Create local commits
        # Mock GitHub remote
        # Assert push successful

    def test_webhook_rate_limiting(self):
        """Test webhook rate limiting."""
        # Send multiple webhook requests
        # Assert only first one triggers pull
        # Assert rate-limited responses

    def test_cleanup_stale_branches(self):
        """Test branch cleanup."""
        # Create old branches
        # Run cleanup
        # Assert old branches deleted
        # Assert active branches kept
```

**2. Update Documentation**
- [ ] Update README.md with Phase 5 status
- [ ] Update IMPLEMENTATION_PLAN.md
- [ ] Update distributed-wiki-project-plan.md
- [ ] Create PHASE_5_SUMMARY.md
- [ ] Update Claude.md with new codes

**3. Create Setup Guide**
```markdown
# GitHub Integration Setup Guide

## SSH Key Setup
1. Generate SSH key: `ssh-keygen -t ed25519 -C "gitwiki@example.com"`
2. Add public key to GitHub: Settings > Deploy Keys
3. Configure GitWiki: Settings > GitHub > SSH Key Path

## GitHub Repository Setup
1. Create GitHub repository
2. Copy repository URL: `git@github.com:user/repo.git`
3. Configure GitWiki: Settings > GitHub > Remote URL

## Webhook Setup
1. GitHub: Settings > Webhooks > Add webhook
2. Payload URL: `https://your-domain.com/api/git/webhook/`
3. Content type: `application/json`
4. Secret: (optional, recommended)
5. Events: Just the push event

## Testing
- Test SSH: Settings > GitHub > Test Connection
- Manual sync: Settings > Sync > Sync Now
- View logs: Check Django logs for [GITOPS-PULL*] codes
```

---

## File Structure

**New Files:**
```
git_service/
├── tasks.py                    # Celery periodic tasks
├── utils.py                    # SSH testing utility
└── templates/git_service/
    ├── sync.html              # Sync management page
    └── github_settings.html   # GitHub configuration

config/
└── celery.py                  # Celery configuration

PHASE_5_PLAN.md               # This file
PHASE_5_SUMMARY.md            # Created at completion
```

**Modified Files:**
```
git_service/
├── git_operations.py          # +400 lines (5 new methods)
├── views.py                   # +150 lines (3 new views)
├── api.py                     # +50 lines (webhook endpoint)
├── urls.py                    # +5 routes
└── tests.py                   # +200 lines (integration tests)

config/
└── settings.py                # Celery & cache configuration

requirements.txt               # +celery, redis, django-celery-beat

Claude.md                      # +20 new grepable codes
distributed-wiki-project-plan.md  # Status update
```

---

## Grepable Codes to Add

**Git Service (20 codes):**
- GITOPS-PULL01 through GITOPS-PULL05 (5 codes)
- GITOPS-PUSH01 through GITOPS-PUSH05 (5 codes)
- GITOPS-CLEANUP01 through GITOPS-CLEANUP05 (5 codes)
- GITOPS-REBUILD01 through GITOPS-REBUILD05 (5 codes)

**Webhook Handler (5 codes):**
- WEBHOOK-01 through WEBHOOK-05

**Celery Tasks (6 codes):**
- TASK-PULL01, TASK-PULL02
- TASK-CLEANUP01, TASK-CLEANUP02
- TASK-REBUILD01, TASK-REBUILD02

**Total:** 31 new codes

---

## AIDEV-NOTEs to Add

```python
# AIDEV-NOTE: github-pull; Handles conflicts during pull gracefully
def pull_from_github(self) -> Dict:
    ...

# AIDEV-NOTE: github-push; Only pushes if local is ahead
def push_to_github(self, branch: str = "main") -> Dict:
    ...

# AIDEV-NOTE: webhook-handler; Rate-limited to 1 pull/minute
def github_webhook_handler(request):
    ...

# AIDEV-NOTE: branch-cleanup; Only removes inactive sessions
def cleanup_stale_branches(self, age_days: int = 7) -> Dict:
    ...

# AIDEV-NOTE: static-rebuild; Atomic operation, old files kept until complete
def full_static_rebuild(self) -> Dict:
    ...
```

**Total:** 5 new AIDEV-NOTEs

---

## Success Criteria

### Functional Requirements
- [ ] Can pull changes from GitHub successfully
- [ ] Can push commits to GitHub successfully
- [ ] Webhook triggers sync (with rate limiting)
- [ ] Periodic tasks running reliably:
  - [ ] GitHub pull every 5 minutes
  - [ ] Branch cleanup daily
  - [ ] Static rebuild weekly
- [ ] Stale branches cleaned up correctly
- [ ] Active sessions preserved during cleanup
- [ ] Full static rebuild completes successfully

### Performance Requirements
- [ ] Pull operation completes in < 10 seconds
- [ ] Push operation completes in < 10 seconds
- [ ] Webhook response in < 2 seconds
- [ ] Cleanup doesn't block other operations
- [ ] Rebuild completes in < 30 seconds for 100 pages

### Quality Requirements
- [ ] All unit tests passing
- [ ] Integration tests for all workflows
- [ ] Proper error handling throughout
- [ ] Comprehensive logging with grepable codes
- [ ] No data loss during operations
- [ ] SSH errors clearly communicated

---

## Risks & Mitigations

### Risk 1: SSH Authentication Failures
**Impact:** High
**Likelihood:** Medium
**Mitigation:**
- Clear setup documentation
- SSH testing utility
- Helpful error messages
- Fallback to manual sync

### Risk 2: Merge Conflicts During Pull
**Impact:** High
**Likelihood:** Medium
**Mitigation:**
- Detect conflicts and notify
- Don't force-pull (preserve local changes)
- Clear conflict resolution workflow
- Log all conflicts

### Risk 3: Webhook Abuse / DDoS
**Impact:** Medium
**Likelihood:** Low
**Mitigation:**
- Rate limiting (1/minute)
- Webhook signature verification
- Caching recent results
- Monitoring and alerts

### Risk 4: Celery Worker Failures
**Impact:** High
**Likelihood:** Low
**Mitigation:**
- Celery monitoring
- Task retry logic
- Manual trigger fallback
- Clear error logging

### Risk 5: Large Repository Performance
**Impact:** Medium
**Likelihood:** Low
**Mitigation:**
- Shallow clones (--depth 1)
- Incremental pulls
- Background task queue
- Performance monitoring

---

## Dependencies

### New Python Packages
```txt
celery==5.3.4
redis==5.0.1
django-celery-beat==2.5.0
django-redis==5.4.0
```

### System Requirements
- Redis server (for Celery broker and cache)
- SSH client (for GitHub authentication)
- Sufficient disk space for full rebuilds

### Configuration Requirements
- GitHub repository created
- SSH key pair generated
- Deploy key added to GitHub
- Webhook configured (optional)

---

## Estimated Effort

**Backend Implementation:** 3-4 days
- pull_from_github(): 4 hours
- push_to_github(): 3 hours
- cleanup_stale_branches(): 4 hours
- full_static_rebuild(): 3 hours
- Webhook handler: 3 hours
- SSH utilities: 2 hours

**Celery Integration:** 2 days
- Celery setup: 4 hours
- Task creation: 3 hours
- Beat scheduler: 2 hours
- Testing: 3 hours

**UI & Configuration:** 1-2 days
- Sync management page: 3 hours
- GitHub settings page: 3 hours
- Testing & refinement: 2-4 hours

**Testing & Documentation:** 2 days
- Integration tests: 4 hours
- Documentation: 4 hours
- User testing: 4 hours

**Total:** 8-10 days

---

## Phase 6 Preparation

After Phase 5, the next phase (Configuration & Permissions) will require:

**Phase 5 Deliverables:**
- ✅ GitHub sync working
- ✅ Periodic tasks reliable
- ✅ Branch cleanup automated
- ✅ Admin UI functional

**Phase 6 Will Add:**
- Permission system (open/read-only/private)
- Configuration UI for all settings
- Enhanced admin interfaces
- User management
- SSH key testing UI

---

## Quick Start for Next Developer

### Day 1: Start Here
```bash
# Checkout branch
git checkout claude/review-project-documentation-011CUUhwTxwUjWRgfxq5UU8s

# Install new dependencies
pip install celery redis django-celery-beat django-redis

# Start Redis
redis-server

# Create git_service/tasks.py
# Create config/celery.py
# Update config/settings.py with Celery config
```

### Day 2-3: Core Operations
```bash
# Implement in git_operations.py:
# 1. pull_from_github()
# 2. push_to_github()
# 3. Write unit tests
# 4. Test with mock remote
```

### Day 4-5: Cleanup & Webhook
```bash
# Implement in git_operations.py:
# 1. cleanup_stale_branches()
# 2. full_static_rebuild()

# Create webhook handler in views.py
# Add webhook URL to urls.py
# Test rate limiting
```

### Day 6-10: Celery & UI
```bash
# Create Celery tasks
# Start Celery worker: celery -A config worker -l info
# Start Celery beat: celery -A config beat -l info
# Create sync management UI
# Create GitHub settings UI
# Integration testing
```

---

**Phase 5 Status:** Ready to Begin
**Priority:** High
**Complexity:** Medium-High
**Estimated Duration:** 8-10 days

---

*Plan created: October 25, 2025*
*Next update: Phase 5 completion*
