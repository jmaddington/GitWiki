# Phase 7 Implementation Plan - Polish & Deployment

**Status:** 📋 Ready to Implement
**Duration:** 2 weeks (14 days)
**Goal:** Production-ready deployment with complete documentation, security audit, and polish
**Priority:** CRITICAL - Final phase before production launch

---

## Executive Summary

Phase 7 is the final phase of the GitWiki project. All core features are complete (Phases 1-6), and this phase focuses on:

1. **Security** - Address vulnerabilities and conduct comprehensive security audit
2. **Reliability** - Professional error handling and edge case coverage
3. **Performance** - Optimization and scalability improvements
4. **Documentation** - Complete user, admin, and developer guides
5. **Deployment** - Production-ready configuration and deployment scripts
6. **Quality** - 80%+ test coverage and load testing

**Current Status:** 80% complete (8 of 10 weeks)
**After Phase 7:** 100% complete, production-ready

---

## Phase 7 Roadmap

### Week 9: Critical Production Readiness (Days 1-7)

- **Days 1-2:** Security Audit & Dependency Updates 🔴 **CRITICAL**
- **Day 3:** Error Pages & Error Handling 🔴 **CRITICAL**
- **Days 4-5:** Performance Optimization
- **Days 6-7:** Testing & Coverage (80%+ goal)

### Week 10: Documentation & Deployment (Days 8-14)

- **Days 8-9:** Comprehensive Documentation 🔴 **CRITICAL**
- **Day 10:** Deployment Preparation
- **Day 11:** UI/UX Polish
- **Day 12:** Pre-Commit Hooks
- **Days 13-14:** Production Deployment

---

## Week 9: Critical Production Readiness

### Days 1-2: Security Audit & Dependency Updates 🔴 **CRITICAL**

**Goal:** Address 30 dependency vulnerabilities and conduct comprehensive security audit

#### Task 1.1: Update Dependencies (4 hours)

**Current Issue:** 30 vulnerabilities (2 critical, 12 high, 14 moderate, 2 low)

**Action Steps:**

```bash
# 1. Check current vulnerabilities
pip list --outdated

# 2. Update all dependencies
pip install --upgrade -r requirements.txt

# 3. Test application after updates
python manage.py test

# 4. Check for remaining vulnerabilities
pip check

# 5. Update requirements.txt with new versions
pip freeze > requirements.txt.new
# Review differences and update requirements.txt

# 6. Test all critical workflows
python manage.py test
python manage.py runserver
# Manual testing: edit, publish, conflict resolution, GitHub sync
```

**Expected Changes:**
- Django: Likely needs update for security patches
- Celery: Check for security updates
- GitPython: Update to latest stable
- All other dependencies: Update within safe version ranges

**Testing Checklist:**
- [ ] All tests pass after updates
- [ ] Editor functionality works (create, edit, save, commit, publish)
- [ ] Conflict resolution works
- [ ] GitHub sync works (pull/push)
- [ ] Celery tasks execute correctly
- [ ] Permission system works (all 3 modes)
- [ ] Admin interface accessible

**Deliverable:** Updated requirements.txt with all vulnerabilities resolved

---

#### Task 1.2: Django Security Settings Review (2 hours)

**File:** `config/settings.py`

**Review Checklist:**

```python
# 1. SECRET_KEY
# Current: Likely hardcoded or from environment
# Action: Ensure SECRET_KEY is from environment variable, not in code

# Add to settings.py if not present:
import os
from pathlib import Path

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set")

# 2. DEBUG
# Current: Likely True for development
# Action: Create production settings

# In config/settings.py (development):
DEBUG = True

# Create config/production_settings.py:
from .settings import *

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# 3. ALLOWED_HOSTS
# Production must specify allowed hosts
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# 4. SECURE_SSL_REDIRECT
# For production with HTTPS:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 5. SECURE_HSTS_SECONDS
# HTTP Strict Transport Security
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 6. X_FRAME_OPTIONS
# Prevent clickjacking
X_FRAME_OPTIONS = 'DENY'

# 7. SECURE_CONTENT_TYPE_NOSNIFF
SECURE_CONTENT_TYPE_NOSNIFF = True

# 8. SECURE_BROWSER_XSS_FILTER
SECURE_BROWSER_XSS_FILTER = True
```

**Action Items:**
- [ ] Create `config/production_settings.py`
- [ ] Move all production-specific settings to production_settings.py
- [ ] Document required environment variables in README.md
- [ ] Test with production settings locally

**Deliverable:** Production-ready settings configuration

---

#### Task 1.3: Security Audit - SQL Injection (1 hour)

**Goal:** Verify no SQL injection vulnerabilities

**Review Areas:**

1. **Django ORM Usage** - ✅ Should be safe (Django ORM escapes by default)
2. **Raw Queries** - Search for `.raw()`, `.extra()`, `cursor.execute()`

```bash
# Search for potential raw SQL
cd /home/user/GitWiki
grep -r "\.raw\(" --include="*.py" .
grep -r "\.extra\(" --include="*.py" .
grep -r "cursor\.execute" --include="*.py" .
```

**Expected:** No raw SQL queries (all use Django ORM)

**If Found:** Review and ensure parameterized queries are used

**Deliverable:** SQL injection audit report

---

#### Task 1.4: Security Audit - XSS Prevention (1 hour)

**Goal:** Verify all user input is escaped in templates

**Review Areas:**

1. **Template Auto-Escaping** - Django templates auto-escape by default
2. **Safe Filter Usage** - Search for `|safe` filter usage

```bash
# Search for |safe filter usage
cd /home/user/GitWiki
grep -r "|safe" --include="*.html" .
grep -r "mark_safe" --include="*.py" .
```

**Action for Each Instance:**
- Verify the content is truly safe (not user-generated)
- If user-generated, remove `|safe` and use appropriate escaping
- Document why `|safe` is necessary if kept

**Deliverable:** XSS audit report with justifications for any `|safe` usage

---

#### Task 1.5: Security Audit - CSRF Protection (30 minutes)

**Goal:** Verify all forms have CSRF protection

**Review:**

```bash
# Search for forms without {% csrf_token %}
cd /home/user/GitWiki
grep -r "<form" --include="*.html" . | grep -v csrf_token
```

**Action:**
- Verify all forms have `{% csrf_token %}`
- Check AJAX requests include CSRF token

**Expected:** All forms protected (Django includes CSRF middleware by default)

**Deliverable:** CSRF audit report

---

#### Task 1.6: Security Audit - Path Traversal (1 hour)

**Goal:** Verify file paths are validated

**Review Files:**
- `editor/serializers.py` - Path validation (AIDEV-NOTE: path-validation)
- `git_service/git_operations.py` - File path handling
- `display/views.py` - File serving

**Check for:**
- `../` in file paths
- Absolute path validation
- Whitelist of allowed directories

**Current Implementation:**
```python
# editor/serializers.py should have path validation
# Verify it prevents:
# - "../../../etc/passwd"
# - "/etc/passwd"
# - "docs/../../secrets.txt"
```

**If Not Present:** Add path validation

```python
import os
from django.core.exceptions import ValidationError

def validate_safe_path(file_path):
    """Prevent path traversal attacks."""
    # Normalize the path
    normalized = os.path.normpath(file_path)

    # Check for absolute paths
    if os.path.isabs(normalized):
        raise ValidationError("Absolute paths not allowed")

    # Check for parent directory references
    if normalized.startswith('..') or '/..' in normalized:
        raise ValidationError("Parent directory references not allowed")

    # Check for hidden files
    if normalized.startswith('.'):
        raise ValidationError("Hidden files not allowed")

    return normalized
```

**Deliverable:** Path traversal audit report

---

#### Task 1.7: Security Audit - SSH Key Handling (30 minutes)

**Goal:** Verify SSH keys are handled securely

**Review:**
- `git_service/utils.py` - SSH key path validation
- File permissions on SSH keys (should be 600)
- SSH key storage (should not be in repository)

**Check:**
- [ ] SSH key path comes from Configuration model, not hardcoded
- [ ] File permissions validated (warn if not 600)
- [ ] SSH key never logged or exposed in API responses

**Deliverable:** SSH security audit report

---

#### Task 1.8: Create Security Audit Report (1 hour)

**File:** `docs/SECURITY_AUDIT.md`

**Template:**

```markdown
# GitWiki Security Audit Report

**Date:** [Current Date]
**Auditor:** [Your Name]
**Scope:** Phase 7 Security Audit

## Executive Summary

This document reports the findings of a comprehensive security audit conducted
on the GitWiki application prior to production deployment.

## Dependency Vulnerabilities

**Status:** ✅ RESOLVED

- Initial vulnerabilities: 30 (2 critical, 12 high, 14 moderate, 2 low)
- Actions taken:
  - Updated Django from X.X.X to X.X.X
  - Updated Celery from X.X.X to X.X.X
  - Updated GitPython from X.X.X to X.X.X
  - [List all updates]
- Remaining vulnerabilities: 0
- Testing: All tests pass, manual testing complete

## SQL Injection

**Status:** ✅ SECURE

- All database queries use Django ORM
- No raw SQL found
- Parameterized queries used throughout

## Cross-Site Scripting (XSS)

**Status:** ✅ SECURE

- Django template auto-escaping enabled
- |safe filter usage reviewed:
  - [List each instance with justification]
- User-generated content properly escaped

## CSRF Protection

**Status:** ✅ SECURE

- All forms include {% csrf_token %}
- AJAX requests include CSRF header
- Django CSRF middleware enabled

## Path Traversal

**Status:** ✅ SECURE

- Path validation implemented in editor/serializers.py
- Prevents ../ and absolute paths
- File serving restricted to allowed directories

## SSH Key Security

**Status:** ✅ SECURE

- SSH key path from Configuration model
- File permissions validated (600 required)
- Keys never exposed in logs or API

## Production Settings

**Status:** ✅ CONFIGURED

- SECRET_KEY from environment variable
- DEBUG = False in production
- ALLOWED_HOSTS configured
- HTTPS enforced (SECURE_SSL_REDIRECT = True)
- Security headers enabled

## Recommendations

1. Regular dependency updates (monthly)
2. Monitor Dependabot alerts
3. Annual security audit
4. Consider adding rate limiting to API endpoints
5. Consider adding security.txt file

## Conclusion

The GitWiki application has been thoroughly audited and is ready for
production deployment with no critical security issues identified.
```

**Deliverable:** Complete security audit report

---

### Day 3: Error Pages & Error Handling 🔴 **CRITICAL**

**Goal:** Professional error handling with custom error pages

#### Task 3.1: Create Custom Error Templates (2 hours)

**Templates to Create:**

1. **templates/404.html** - Page Not Found
2. **templates/500.html** - Internal Server Error
3. **templates/403.html** - Permission Denied

**Design Requirements:**
- Consistent with GitWiki branding (Bootstrap 5)
- Helpful error messages
- Navigation back to home
- Search box (for 404)
- Contact information or support link

**Example: templates/404.html**

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Not Found - GitWiki</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .error-container {
            background: white;
            border-radius: 10px;
            padding: 3rem;
            max-width: 600px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .error-code {
            font-size: 6rem;
            font-weight: bold;
            color: #667eea;
            margin: 0;
        }
        .error-title {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #333;
        }
        .error-message {
            color: #666;
            margin-bottom: 2rem;
        }
        .search-box {
            margin: 2rem 0;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">404</h1>
        <h2 class="error-title">Page Not Found</h2>
        <p class="error-message">
            The page you're looking for doesn't exist or has been moved.
            Try searching for it or head back to the home page.
        </p>

        <div class="search-box">
            <form action="{% url 'display:search' %}" method="get" class="d-flex gap-2">
                <input type="text" name="q" class="form-control" placeholder="Search the wiki...">
                <button type="submit" class="btn btn-primary">Search</button>
            </form>
        </div>

        <div class="d-grid gap-2">
            <a href="/" class="btn btn-lg btn-primary">
                <i class="fas fa-home"></i> Go to Home Page
            </a>
            <a href="/editor/sessions/" class="btn btn-lg btn-outline-secondary">
                View My Drafts
            </a>
        </div>

        <p class="mt-4 text-muted small">
            If you believe this is an error, please contact your administrator.
        </p>
    </div>

    <script src="https://kit.fontawesome.com/your-kit.js" crossorigin="anonymous"></script>
</body>
</html>
```

**Example: templates/500.html**

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Internal Server Error - GitWiki</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .error-container {
            background: white;
            border-radius: 10px;
            padding: 3rem;
            max-width: 600px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .error-code {
            font-size: 6rem;
            font-weight: bold;
            color: #f5576c;
            margin: 0;
        }
        .error-title {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #333;
        }
        .error-message {
            color: #666;
            margin-bottom: 2rem;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">500</h1>
        <h2 class="error-title">Internal Server Error</h2>
        <p class="error-message">
            Oops! Something went wrong on our end. Our team has been notified
            and we're working to fix it. Please try again in a few moments.
        </p>

        <div class="d-grid gap-2">
            <a href="/" class="btn btn-lg btn-primary">
                <i class="fas fa-home"></i> Go to Home Page
            </a>
            <button onclick="window.location.reload()" class="btn btn-lg btn-outline-secondary">
                <i class="fas fa-redo"></i> Try Again
            </button>
        </div>

        <p class="mt-4 text-muted small">
            Error ID: {{ request_id }}<br>
            If this problem persists, please contact your administrator with this error ID.
        </p>
    </div>

    <script src="https://kit.fontawesome.com/your-kit.js" crossorigin="anonymous"></script>
</body>
</html>
```

**Example: templates/403.html**

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied - GitWiki</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .error-container {
            background: white;
            border-radius: 10px;
            padding: 3rem;
            max-width: 600px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .error-code {
            font-size: 6rem;
            font-weight: bold;
            color: #fa709a;
            margin: 0;
        }
        .error-title {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #333;
        }
        .error-message {
            color: #666;
            margin-bottom: 2rem;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">403</h1>
        <h2 class="error-title">Access Denied</h2>
        <p class="error-message">
            You don't have permission to access this page. This wiki may require
            authentication or you may need additional permissions.
        </p>

        <div class="d-grid gap-2">
            <a href="/accounts/login/?next={{ request.path }}" class="btn btn-lg btn-primary">
                <i class="fas fa-sign-in-alt"></i> Log In
            </a>
            <a href="/" class="btn btn-lg btn-outline-secondary">
                <i class="fas fa-home"></i> Go to Home Page
            </a>
        </div>

        <p class="mt-4 text-muted small">
            If you believe you should have access, please contact your administrator.
        </p>
    </div>

    <script src="https://kit.fontawesome.com/your-kit.js" crossorigin="anonymous"></script>
</body>
</html>
```

**Configuration in settings.py:**

```python
# config/settings.py

# Debug toolbar (development only)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Custom error handlers (production)
# Django automatically uses these templates:
# - 404.html for 404 errors
# - 500.html for 500 errors
# - 403.html for 403 errors
# - 400.html for 400 errors (optional)
```

**Testing Error Pages:**

```python
# config/urls.py - Add these for testing only

from django.conf import settings

if settings.DEBUG:
    # Test error pages in development
    urlpatterns += [
        path('test-404/', lambda request: render(request, '404.html')),
        path('test-500/', lambda request: render(request, '500.html')),
        path('test-403/', lambda request: render(request, '403.html')),
    ]
```

**Deliverable:** Professional error pages for 404, 500, 403

---

#### Task 3.2: Graceful Error Handling in Views (3 hours)

**Goal:** Add try/except blocks with user-friendly error messages

**Files to Review:**
- `git_service/views.py`
- `editor/views.py`
- `display/views.py`
- `git_service/api.py`
- `editor/api.py`

**Pattern to Implement:**

```python
import logging
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect

logger = logging.getLogger(__name__)

def example_view(request):
    """Example of proper error handling."""
    try:
        # Main logic here
        result = perform_operation()

        return JsonResponse({
            'success': True,
            'data': result
        })

    except PermissionError as e:
        # Specific error handling
        logger.warning(f"Permission denied: {str(e)} [EXAMPLE-VIEW01]")
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to perform this action.',
            'code': 'PERMISSION_DENIED'
        }, status=403)

    except FileNotFoundError as e:
        # File not found
        logger.warning(f"File not found: {str(e)} [EXAMPLE-VIEW02]")
        return JsonResponse({
            'success': False,
            'error': 'The requested file does not exist.',
            'code': 'FILE_NOT_FOUND'
        }, status=404)

    except ValidationError as e:
        # Validation error
        logger.info(f"Validation error: {str(e)} [EXAMPLE-VIEW03]")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'VALIDATION_ERROR'
        }, status=422)

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in example_view: {str(e)} [EXAMPLE-VIEW04]", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again or contact support.',
            'code': 'INTERNAL_ERROR'
        }, status=500)
```

**For Template Views:**

```python
def example_template_view(request):
    """Example of error handling for template views."""
    try:
        # Main logic
        data = get_data()

        return render(request, 'example.html', {
            'data': data
        })

    except PermissionError:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    except FileNotFoundError:
        # Let Django handle with 404.html
        raise Http404("Page not found")

    except Exception as e:
        logger.error(f"Error in example_template_view: {str(e)} [EXAMPLE-VIEW05]", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')
        return redirect('home')
```

**Areas to Add Error Handling:**

1. **display/views.py:**
   - wiki_page(): Handle missing files gracefully
   - wiki_search(): Handle search errors
   - page_history(): Handle Git errors

2. **editor/views.py:**
   - edit_page(): Handle session creation errors
   - list_sessions(): Handle database errors

3. **git_service/views.py:**
   - sync_management(): Handle Git errors
   - github_settings(): Handle SSH connection errors

**Testing:**
- [ ] Test each error path
- [ ] Verify user-friendly messages displayed
- [ ] Verify errors logged with grepable codes
- [ ] Test error pages in production mode

**Deliverable:** Graceful error handling across all views

---

#### Task 3.3: Add Grepable Logging Codes (1 hour)

**Goal:** Ensure all new error handlers have unique grepable codes

**Review:**
- Check all new logger calls have unique codes
- Document new codes in Claude.md
- Follow pattern: `[COMPONENT-ACTION##]`

**Example New Codes:**
```
ERROR-404-01: Page not found in static files
ERROR-500-01: Unexpected error in view
ERROR-403-01: Permission denied in middleware
```

**Update Claude.md:**

```markdown
Error Handling:
- ERROR-404-01: Page not found in static files
- ERROR-500-01: Unexpected error in view
- ERROR-403-01: Permission denied in middleware
- ERROR-PAGE01: Custom error page rendered
```

**Deliverable:** All error handlers have grepable codes, Claude.md updated

---

### Days 4-5: Performance Optimization

**Goal:** Improve performance with database indexes, query optimization, and caching

#### Task 4.1: Database Indexes (2 hours)

**Files to Create:**
- `git_service/migrations/000X_add_performance_indexes.py`
- `editor/migrations/000X_add_performance_indexes.py`

**Analysis:**

1. **GitOperation Model** - High read volume for audit logs

```python
# git_service/models.py

class GitOperation(models.Model):
    # ... existing fields ...

    class Meta:
        # Add these indexes
        indexes = [
            models.Index(fields=['timestamp'], name='gitop_timestamp_idx'),
            models.Index(fields=['operation_type', 'timestamp'], name='gitop_type_time_idx'),
            models.Index(fields=['user', 'timestamp'], name='gitop_user_time_idx'),
            models.Index(fields=['success', 'timestamp'], name='gitop_success_time_idx'),
        ]
        ordering = ['-timestamp']
```

2. **EditSession Model** - Frequently queried by user and status

```python
# editor/models.py

class EditSession(models.Model):
    # ... existing fields ...

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active'], name='editsess_user_active_idx'),
            models.Index(fields=['is_active', 'last_modified'], name='editsess_active_modified_idx'),
            models.Index(fields=['branch_name'], name='editsess_branch_idx'),
        ]
        ordering = ['-last_modified']
```

3. **Configuration Model** - Small table, index on key

```python
# git_service/models.py

class Configuration(models.Model):
    # ... existing fields ...

    class Meta:
        indexes = [
            models.Index(fields=['key'], name='config_key_idx'),
        ]
```

**Create Migration:**

```bash
python manage.py makemigrations --name add_performance_indexes
python manage.py migrate
```

**Test:**

```bash
# Check indexes created
python manage.py dbshell
# In PostgreSQL:
\d git_service_gitoperation
\d editor_editsession
\d git_service_configuration
```

**Deliverable:** Database indexes added and migrated

---

#### Task 4.2: Query Optimization (3 hours)

**Goal:** Optimize database queries with select_related and prefetch_related

**File:** `git_service/admin.py`

**Current Issue:** N+1 queries in admin

**Fix:**

```python
# git_service/admin.py

@admin.register(GitOperation)
class GitOperationAdmin(admin.ModelAdmin):
    list_display = ['id', 'operation_type', 'username', 'branch_name',
                    'success_badge', 'execution_time_colored', 'timestamp']
    list_filter = ['operation_type', 'success', 'timestamp']
    search_fields = ['branch_name', 'file_path', 'user__username', 'error_message']
    readonly_fields = ['timestamp', 'execution_time_ms']
    date_hierarchy = 'timestamp'

    def get_queryset(self, request):
        # Optimize: select_related for foreign keys
        qs = super().get_queryset(request)
        return qs.select_related('user')  # Avoid N+1 queries

    def username(self, obj):
        return obj.user.username if obj.user else 'System'
    username.short_description = 'User'
    username.admin_order_field = 'user__username'
```

**File:** `editor/admin.py`

```python
# editor/admin.py

@admin.register(EditSession)
class EditSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'file_path_short', 'branch_name',
                    'status_badge', 'session_age_colored', 'last_modified']
    list_filter = ['is_active', 'created_at', 'last_modified']
    search_fields = ['user__username', 'file_path', 'branch_name']
    readonly_fields = ['created_at', 'last_modified']
    actions = ['delete_inactive_sessions']

    def get_queryset(self, request):
        # Optimize: select_related for foreign keys
        qs = super().get_queryset(request)
        return qs.select_related('user')  # Avoid N+1 queries

    def username(self, obj):
        return obj.user.username
    username.short_description = 'User'
    username.admin_order_field = 'user__username'
```

**File:** `editor/views.py`

```python
# editor/views.py

def list_sessions(request):
    """List all active editing sessions for current user."""
    if not request.user.is_authenticated:
        return redirect('login')

    # Optimize: select_related for user
    sessions = EditSession.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('user').order_by('-last_modified')

    return render(request, 'editor/sessions.html', {
        'sessions': sessions
    })
```

**File:** `display/views.py`

**No foreign keys, but optimize file operations:**

```python
# display/views.py

from django.core.cache import cache

def wiki_search(request):
    """Search wiki pages with caching."""
    query = request.GET.get('q', '').strip()
    page_num = int(request.GET.get('page', 1))

    if not query:
        return render(request, 'display/search.html', {'query': ''})

    # Cache search results for 5 minutes
    cache_key = f'search:{query}:{page_num}'
    results = cache.get(cache_key)

    if results is None:
        # Perform search
        results = perform_search(query)
        cache.set(cache_key, results, 300)  # 5 minutes

    # ... rest of view
```

**Deliverable:** Optimized queries with select_related/prefetch_related

---

#### Task 4.3: Caching Strategy (2 hours)

**Goal:** Implement caching for expensive operations

**File:** `config/settings.py`

**Cache Configuration:**

```python
# config/settings.py

# Cache configuration (already exists for conflict caching)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'gitwiki',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Cache timeouts for different operations
CACHE_TIMEOUT_SEARCH = 300  # 5 minutes
CACHE_TIMEOUT_CONFLICTS = 120  # 2 minutes (already implemented)
CACHE_TIMEOUT_PAGE_HISTORY = 600  # 10 minutes
CACHE_TIMEOUT_DIRECTORY_LISTING = 300  # 5 minutes
```

**Areas to Cache:**

1. **Search Results** (already shown above in wiki_search)

2. **Page History:**

```python
# display/views.py

from django.core.cache import cache

def page_history(request, file_path):
    """Show commit history for a page with caching."""
    # Cache key
    cache_key = f'history:{file_path}'
    history = cache.get(cache_key)

    if history is None:
        # Get from Git
        repo = get_repository()
        history = repo.get_file_history(file_path, branch='main', limit=50)
        cache.set(cache_key, history, settings.CACHE_TIMEOUT_PAGE_HISTORY)

    # ... rest of view
```

3. **Directory Listings:**

```python
# display/views.py

def wiki_page(request, file_path=''):
    """Display a wiki page with cached directory listing."""
    # ... existing code ...

    # Cache directory listing
    if is_directory:
        cache_key = f'dir_list:{file_path}'
        dir_contents = cache.get(cache_key)

        if dir_contents is None:
            dir_contents = _list_directory(full_path)
            cache.set(cache_key, dir_contents, settings.CACHE_TIMEOUT_DIRECTORY_LISTING)

    # ... rest of view
```

4. **Configuration Values:**

```python
# git_service/models.py

from django.core.cache import cache

class Configuration(models.Model):
    # ... existing fields ...

    @classmethod
    def get_config(cls, key, default=None):
        """Get configuration value with caching."""
        cache_key = f'config:{key}'
        value = cache.get(cache_key)

        if value is None:
            try:
                config = cls.objects.get(key=key)
                value = config.value
                # Cache for 1 hour
                cache.set(cache_key, value, 3600)
            except cls.DoesNotExist:
                value = default

        return value

    @classmethod
    def set_config(cls, key, value, description=''):
        """Set configuration value and invalidate cache."""
        config, created = cls.objects.update_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )

        # Invalidate cache
        cache_key = f'config:{key}'
        cache.delete(cache_key)

        return config
```

**Cache Invalidation:**

```python
# git_service/git_operations.py

def publish_draft(self, branch_name, auto_push=True):
    """Publish draft with cache invalidation."""
    # ... existing code ...

    if merge_result['success']:
        # Invalidate caches
        from django.core.cache import cache
        cache.delete_pattern('search:*')
        cache.delete_pattern('history:*')
        cache.delete_pattern('dir_list:*')

        # ... rest of code
```

**Deliverable:** Caching implemented for expensive operations

---

#### Task 4.4: Profile and Optimize Slow Endpoints (2 hours)

**Goal:** Identify and optimize slow endpoints

**Install Django Debug Toolbar:**

```bash
pip install django-debug-toolbar
```

**Configure:**

```python
# config/settings.py

if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']

# config/urls.py

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
```

**Profile Key Endpoints:**

1. Start server with debug toolbar:
```bash
python manage.py runserver
```

2. Test each endpoint and note:
   - Number of queries
   - Query time
   - Cache hits/misses
   - Total render time

3. Optimize as needed:
   - Reduce queries with select_related/prefetch_related
   - Add indexes
   - Implement caching
   - Optimize template rendering

**Target Performance:**
- Page load: < 200ms
- Search: < 500ms
- Edit session start: < 2 seconds
- Conflict detection: < 30 seconds (already cached)

**Deliverable:** Performance report with optimizations

---

### Days 6-7: Testing & Coverage

**Goal:** Achieve 80%+ test coverage

#### Task 6.1: Install Coverage.py (30 minutes)

```bash
pip install coverage
```

**Create .coveragerc:**

```ini
# .coveragerc

[run]
source = .
omit =
    */migrations/*
    */tests.py
    */tests/*
    */venv/*
    */virtualenv/*
    manage.py
    */config/wsgi.py
    */config/asgi.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstract
```

**Run Coverage:**

```bash
# Run tests with coverage
coverage run --source='.' manage.py test

# Generate report
coverage report

# Generate HTML report
coverage html

# Open in browser
open htmlcov/index.html
```

**Deliverable:** Coverage report showing current coverage

---

#### Task 6.2: Write Missing Tests (8 hours)

**Goal:** Add tests to reach 80%+ coverage

**Priority Areas:**

1. **git_service/views.py** - sync_management, github_settings, configuration_page
2. **display/views.py** - wiki_page, wiki_search, page_history
3. **config/middleware.py** - Permission middleware (add more edge cases)

**Example: Test sync_management view**

```python
# git_service/tests.py

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class SyncManagementViewTests(TestCase):
    """Tests for sync management view."""

    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            password='testpass',
            is_staff=True,
            is_superuser=True
        )

    def test_sync_page_requires_authentication(self):
        """Sync page should require authentication."""
        response = self.client.get(reverse('git_service:sync_management'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_sync_page_requires_staff(self):
        """Sync page should require staff privileges."""
        # Create non-staff user
        user = User.objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')

        response = self.client.get(reverse('git_service:sync_management'))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_sync_page_accessible_to_staff(self):
        """Sync page should be accessible to staff."""
        self.client.login(username='admin', password='testpass')

        response = self.client.get(reverse('git_service:sync_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sync Management')

    def test_manual_pull_triggers_task(self):
        """Manual pull should trigger pull task."""
        self.client.login(username='admin', password='testpass')

        response = self.client.post(reverse('git_service:manual_pull'))
        self.assertEqual(response.status_code, 302)  # Redirect

        # Check task was triggered (mock in real implementation)
        # from git_service.tasks import pull_from_github_task
        # pull_from_github_task.assert_called_once()
```

**Example: Test display views**

```python
# display/tests.py

from django.test import TestCase, Client
from django.urls import reverse
import os
import tempfile

class DisplayViewTests(TestCase):
    """Tests for display service views."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()

        # Create temporary static files
        self.temp_dir = tempfile.mkdtemp()
        # ... create test HTML files

    def test_wiki_home_loads(self):
        """Wiki home page should load successfully."""
        response = self.client.get(reverse('display:home'))
        self.assertEqual(response.status_code, 200)

    def test_wiki_page_displays_content(self):
        """Wiki page should display markdown content."""
        response = self.client.get(reverse('display:page', args=['test-page']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Page Content')

    def test_wiki_page_404_for_missing(self):
        """Missing wiki page should return 404."""
        response = self.client.get(reverse('display:page', args=['nonexistent']))
        self.assertEqual(response.status_code, 404)

    def test_search_returns_results(self):
        """Search should return matching pages."""
        response = self.client.get(reverse('display:search'), {'q': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Search Results')

    def test_search_pagination(self):
        """Search should paginate results."""
        response = self.client.get(reverse('display:search'), {
            'q': 'test',
            'page': 2
        })
        self.assertEqual(response.status_code, 200)
```

**Areas Needing Tests:**

1. **Permission middleware:**
   - [ ] Test all 3 modes (open, read_only_public, private)
   - [ ] Test edge cases (invalid mode, missing config)
   - [ ] Test exempted paths

2. **Configuration management:**
   - [ ] Test config page loads
   - [ ] Test config updates
   - [ ] Test validation

3. **Display views:**
   - [ ] Test page rendering
   - [ ] Test search functionality
   - [ ] Test history display
   - [ ] Test breadcrumb generation
   - [ ] Test directory listing

4. **Error handling:**
   - [ ] Test 404 scenarios
   - [ ] Test 500 scenarios
   - [ ] Test 403 scenarios

**Deliverable:** 80%+ test coverage

---

#### Task 6.3: Load Testing (3 hours)

**Goal:** Test with concurrent users

**Install locust:**

```bash
pip install locust
```

**Create locustfile.py:**

```python
# locustfile.py

from locust import HttpUser, task, between
import random

class WikiUser(HttpUser):
    """Simulated wiki user."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Login on start."""
        self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'testpass'
        })

    @task(3)
    def view_page(self):
        """View a random page (most common action)."""
        pages = ['home', 'docs/getting-started', 'docs/api', 'about']
        page = random.choice(pages)
        self.client.get(f'/wiki/{page}')

    @task(2)
    def search(self):
        """Search the wiki."""
        queries = ['install', 'configuration', 'api', 'tutorial']
        query = random.choice(queries)
        self.client.get(f'/search/?q={query}')

    @task(1)
    def edit_page(self):
        """Start editing a page."""
        self.client.get('/editor/edit/docs/test')

    @task(1)
    def view_history(self):
        """View page history."""
        self.client.get('/history/docs/getting-started')

    @task(1)
    def list_sessions(self):
        """View editing sessions."""
        self.client.get('/editor/sessions/')
```

**Run Load Test:**

```bash
# Start locust
locust -f locustfile.py

# Open browser
open http://localhost:8089

# Configure:
# - Number of users: 10
# - Spawn rate: 2/second
# - Host: http://localhost:8000

# Run for 5 minutes and analyze results
```

**Monitor During Test:**
- Response times
- Error rate
- Requests per second
- Database connections
- Memory usage

**Performance Targets:**
- 95th percentile response time < 2 seconds
- Error rate < 1%
- Support 10+ concurrent users

**Deliverable:** Load testing report

---

#### Task 6.4: Large Repository Testing (2 hours)

**Goal:** Test with 100+ pages

**Create Test Script:**

```python
# scripts/generate_test_content.py

import os
from git import Repo

def generate_test_wiki(num_pages=100):
    """Generate test wiki content."""
    repo_path = '/path/to/test/repo'
    repo = Repo(repo_path)

    for i in range(num_pages):
        # Create page
        file_path = f'docs/test-page-{i:03d}.md'
        full_path = os.path.join(repo_path, file_path)

        with open(full_path, 'w') as f:
            f.write(f"""# Test Page {i}

This is test page number {i}.

## Section 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 2

```python
def hello():
    print("Hello world")
```

## Section 3

More content here.
""")

        # Commit
        repo.index.add([file_path])
        repo.index.commit(f'Add test page {i}')

    print(f'Generated {num_pages} test pages')

if __name__ == '__main__':
    generate_test_wiki()
```

**Test:**

```bash
# Generate content
python scripts/generate_test_content.py

# Regenerate static files
python manage.py shell
>>> from git_service.git_operations import get_repository
>>> repo = get_repository()
>>> repo.write_branch_to_disk('main')

# Test search performance
curl "http://localhost:8000/search/?q=test"

# Test navigation
# - Load home page
# - Navigate through directories
# - View multiple pages
```

**Measure:**
- Static file generation time (target < 10 seconds for 100 pages)
- Search performance (target < 500ms)
- Page load times
- Directory listing performance

**Deliverable:** Large repository performance report

---

## Week 10: Documentation & Deployment

### Days 8-9: Comprehensive Documentation 🔴 **CRITICAL**

**Goal:** Complete user, admin, and developer documentation

#### Task 8.1: User Documentation (4 hours)

**Create docs/user/ directory:**

```bash
mkdir -p docs/user
```

**1. docs/user/getting-started.md**

```markdown
# Getting Started with GitWiki

Welcome to GitWiki! This guide will help you get started using the wiki.

## What is GitWiki?

GitWiki is a Git-backed wiki system that allows you to create, edit, and collaborate
on markdown documentation with version control.

## Accessing the Wiki

1. Open your web browser and navigate to [your wiki URL]
2. If authentication is required, log in with your credentials

## Viewing Pages

- **Home Page:** Click the GitWiki logo to return to the home page
- **Navigation:** Use the breadcrumb trail at the top to navigate
- **Search:** Use the search box in the navigation bar
- **Directory Listing:** Sidebar shows available pages

## Permission Levels

Your wiki may be configured with one of these permission levels:

- **Open:** Anyone can view and edit pages
- **Read-Only Public:** Anyone can view, login required to edit
- **Private:** Login required to view and edit

Contact your administrator if you need access.

## Next Steps

- [Editing Pages](editing-pages.md)
- [Uploading Images](uploading-images.md)
- [Resolving Conflicts](resolving-conflicts.md)
```

**2. docs/user/editing-pages.md**

```markdown
# Editing Pages

This guide explains how to create and edit wiki pages.

## Starting an Edit

1. Navigate to the page you want to edit
2. Click the "Edit" button
3. The markdown editor will open

## The Editor

GitWiki uses SimpleMDE, a user-friendly markdown editor with:

- **Toolbar:** Quick access to formatting options
- **Preview:** See how your page will look
- **Auto-save:** Your work is automatically saved every 60 seconds

## Markdown Basics

### Headers

```markdown
# Heading 1
## Heading 2
### Heading 3
```

### Text Formatting

```markdown
**Bold text**
*Italic text*
~~Strikethrough~~
`Inline code`
```

### Lists

```markdown
- Unordered list item
- Another item
  - Nested item

1. Ordered list item
2. Another item
```

### Links

```markdown
[Link text](https://example.com)
[Wiki page link](docs/other-page.md)
```

### Code Blocks

````markdown
```python
def hello():
    print("Hello world")
```
````

### Tables

```markdown
| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |
```

## Saving Your Work

### Auto-Save

- Your work is automatically saved to your browser every 60 seconds
- Look for the "Saved" badge in the editor

### Commit to Draft

- Click "Commit" button
- Enter a commit message describing your changes
- Your changes are saved to a draft branch

### Publish

- Click "Publish" button
- Your changes are merged to the main wiki
- If there's a conflict, you'll be prompted to resolve it

## Keyboard Shortcuts

- **Ctrl+S:** Save/Commit
- **Ctrl+P:** Preview
- **F11:** Fullscreen

## Tips

- Write clear commit messages
- Preview your changes before publishing
- Use headings to structure your content
- Keep paragraphs concise
```

**3. docs/user/uploading-images.md**

```markdown
# Uploading Images

GitWiki supports three ways to add images to your pages.

## Method 1: Paste from Clipboard

The easiest way to add screenshots!

1. Take a screenshot (or copy any image)
2. Click in the editor where you want the image
3. Press **Ctrl+V** (Cmd+V on Mac)
4. The image is automatically uploaded
5. Markdown syntax is inserted: `![alt text](path/to/image.png)`

## Method 2: Drag and Drop

1. Open the file manager with your image
2. Drag the image into the editor
3. Drop it where you want it to appear
4. The image is automatically uploaded

## Method 3: File Selector

1. Click the "Upload Image" button in the toolbar
2. Browse and select your image file
3. Click "Open"
4. The image is automatically uploaded

## Supported Formats

- PNG (.png)
- WebP (.webp)
- JPEG (.jpg, .jpeg)

## Size Limit

Maximum file size: 10 MB (configurable by administrator)

## Editing Image Markdown

After upload, you can edit the markdown to:

- Add alt text: `![Description of image](path.png)`
- Resize: Use HTML: `<img src="path.png" width="500">`
- Align: Use HTML: `<img src="path.png" align="right">`

## Tips

- Use descriptive alt text for accessibility
- Compress large images before uploading
- Use PNG for screenshots, JPEG for photos
```

**4. docs/user/resolving-conflicts.md**

```markdown
# Resolving Conflicts

When multiple people edit the same page, conflicts can occur. GitWiki helps you resolve them.

## What is a Conflict?

A conflict happens when:

1. You start editing a page
2. Someone else publishes changes to the same page
3. You try to publish your changes

## Conflict Notification

When you try to publish and there's a conflict, you'll see:

- **Error message:** "Conflict detected"
- **Resolve button:** Click to open the conflict resolution interface

## Resolving Text Conflicts

GitWiki uses Monaco Editor for text conflicts:

### Three-Way Diff

You'll see three versions:

- **Base:** Original version before either edit
- **Theirs:** The published version
- **Yours:** Your version

### Resolution Options

1. **Keep yours:** Your changes win
2. **Keep theirs:** Accept the published version
3. **Merge both:** Combine both changes manually

### Steps

1. Review all three versions
2. Edit the merged version in the right pane
3. Click "Save Resolution"
4. Your changes are published

## Resolving Image Conflicts

For images, you'll see:

- Side-by-side preview of both images
- File size and dimensions
- Radio buttons to choose: "Keep Mine" or "Keep Theirs"

## Tips

- Communicate with other editors
- Commit and publish frequently (less chance of conflicts)
- Use clear commit messages
- When in doubt, keep the more recent changes

## Getting Help

If you're unsure how to resolve a conflict, contact your administrator.
```

**5. docs/user/faq.md**

```markdown
# Frequently Asked Questions

## General

### What is GitWiki?

GitWiki is a wiki system backed by Git version control, allowing you to create
and edit documentation with full history tracking.

### Do I need to know Git?

No! GitWiki provides a user-friendly web interface. Git operations happen
automatically in the background.

### What is markdown?

Markdown is a simple formatting syntax. See our [Editing Pages](editing-pages.md) guide.

## Editing

### Will I lose my work if I close the browser?

No! GitWiki auto-saves to your browser every 60 seconds. When you return,
your work will be restored.

### How do I delete a page?

Contact your administrator to delete pages. This prevents accidental deletions.

### Can I see who edited a page?

Yes! Click "View History" to see all edits, authors, and dates.

### What happens to my drafts?

Drafts are stored until you publish or discard them. You can resume editing
at any time from the "My Drafts" page.

## Images

### What image formats are supported?

PNG, WebP, and JPEG. Maximum size is 10 MB.

### Can I paste screenshots?

Yes! Press Ctrl+V in the editor to paste from clipboard.

### How do I resize images?

Use HTML syntax: `<img src="path.png" width="500">`

## Conflicts

### What causes conflicts?

Conflicts occur when multiple people edit the same page simultaneously.

### How do I avoid conflicts?

- Publish changes frequently
- Communicate with other editors
- Use specific commit messages

### Can conflicts cause data loss?

No! All versions are preserved. You can always access the history.

## Technical

### Can I edit pages offline?

Not currently. GitWiki requires an internet connection.

### Can I use my own markdown editor?

Yes! Clone the Git repository and edit locally, then push changes.

### How is the wiki backed up?

The wiki is stored in a Git repository. Your administrator should have
backup procedures in place.

## Getting Help

Contact your wiki administrator for help or questions not covered here.
```

**Deliverable:** Complete user documentation (5 guides)

---

#### Task 8.2: Admin Documentation (4 hours)

**Create docs/admin/ directory:**

**1. docs/admin/installation.md**

```markdown
# GitWiki Installation Guide

This guide walks you through installing GitWiki on a production server.

## Prerequisites

- Ubuntu 20.04 or later (or equivalent Linux distribution)
- Python 3.10+
- PostgreSQL 12+ (or SQLite for smaller deployments)
- Redis 6+
- Git
- Nginx
- Domain name with DNS configured

## System Preparation

### 1. Update System

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Dependencies

```bash
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib redis-server nginx
```

### 3. Create GitWiki User

```bash
sudo useradd -m -s /bin/bash gitwiki
sudo su - gitwiki
```

## Installation

### 1. Clone Repository

```bash
cd /home/gitwiki
git clone https://github.com/yourusername/GitWiki.git
cd GitWiki
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 4. Configure Database

#### Create PostgreSQL Database

```bash
sudo -u postgres psql

postgres=# CREATE DATABASE gitwiki;
postgres=# CREATE USER gitwiki WITH PASSWORD 'secure_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE gitwiki TO gitwiki;
postgres=# \q
```

### 5. Configure Environment Variables

Create `.env` file:

```bash
nano /home/gitwiki/GitWiki/.env
```

Contents:

```env
DJANGO_SECRET_KEY=your-secret-key-here-generate-with-python-secrets
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://gitwiki:secure_password@localhost/gitwiki
REDIS_URL=redis://localhost:6379/0
```

Generate secret key:

```python
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 9. Initialize Configuration

```bash
python manage.py shell
>>> from git_service.models import Configuration
>>> Configuration.set_config('wiki_title', 'My Wiki', 'Wiki title')
>>> Configuration.set_config('permission_level', 'read_only_public', 'Permission level')
>>> exit()
```

### 10. Initialize Git Repository

```bash
mkdir -p /home/gitwiki/wiki-repo
cd /home/gitwiki/wiki-repo
git init
git config user.name "GitWiki"
git config user.email "gitwiki@yourdomain.com"
git config commit.gpgsign false
echo "# Welcome" > README.md
git add README.md
git commit -m "Initial commit"
```

## Configure Services

### 1. Gunicorn Service

Create `/etc/systemd/system/gitwiki.service`:

```ini
[Unit]
Description=GitWiki Gunicorn Service
After=network.target

[Service]
User=gitwiki
Group=gitwiki
WorkingDirectory=/home/gitwiki/GitWiki
Environment="PATH=/home/gitwiki/GitWiki/venv/bin"
EnvironmentFile=/home/gitwiki/GitWiki/.env
ExecStart=/home/gitwiki/GitWiki/venv/bin/gunicorn --workers 3 --bind unix:/home/gitwiki/GitWiki/gitwiki.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 2. Celery Worker Service

Create `/etc/systemd/system/gitwiki-celery.service`:

```ini
[Unit]
Description=GitWiki Celery Worker
After=network.target redis.service

[Service]
User=gitwiki
Group=gitwiki
WorkingDirectory=/home/gitwiki/GitWiki
Environment="PATH=/home/gitwiki/GitWiki/venv/bin"
EnvironmentFile=/home/gitwiki/GitWiki/.env
ExecStart=/home/gitwiki/GitWiki/venv/bin/celery -A config worker -l info

[Install]
WantedBy=multi-user.target
```

### 3. Celery Beat Service

Create `/etc/systemd/system/gitwiki-celerybeat.service`:

```ini
[Unit]
Description=GitWiki Celery Beat
After=network.target redis.service

[Service]
User=gitwiki
Group=gitwiki
WorkingDirectory=/home/gitwiki/GitWiki
Environment="PATH=/home/gitwiki/GitWiki/venv/bin"
EnvironmentFile=/home/gitwiki/GitWiki/.env
ExecStart=/home/gitwiki/GitWiki/venv/bin/celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

[Install]
WantedBy=multi-user.target
```

### 4. Start Services

```bash
sudo systemctl start gitwiki
sudo systemctl start gitwiki-celery
sudo systemctl start gitwiki-celerybeat
sudo systemctl enable gitwiki
sudo systemctl enable gitwiki-celery
sudo systemctl enable gitwiki-celerybeat
```

### 5. Configure Nginx

Create `/etc/nginx/sites-available/gitwiki`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 20M;

    location /static/ {
        alias /home/gitwiki/GitWiki/staticfiles/;
    }

    location /media/ {
        alias /home/gitwiki/GitWiki/media/;
    }

    location / {
        proxy_pass http://unix:/home/gitwiki/GitWiki/gitwiki.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/gitwiki /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Verification

1. Open browser: `https://yourdomain.com`
2. Verify home page loads
3. Log in as superuser
4. Test editing a page
5. Check `/admin/` interface

## Troubleshooting

Check logs:

```bash
sudo journalctl -u gitwiki -f
sudo journalctl -u gitwiki-celery -f
tail -f /var/log/nginx/error.log
```

## Next Steps

- [Configuration Guide](configuration.md)
- [GitHub Setup](github-setup.md)
- [Backup Procedures](backup-restore.md)
```

**2. docs/admin/configuration.md** (excerpt)

```markdown
# GitWiki Configuration Guide

## Accessing Configuration

1. Log in as administrator
2. Navigate to `/api/git/settings/config/`
3. Or use Django admin: `/admin/`

## Permission Levels

### Open Mode
- No authentication required
- Anyone can view and edit
- **Use case:** Public collaborative wikis

### Read-Only Public
- No authentication to view
- Authentication required to edit
- **Use case:** Public documentation (recommended)

### Private
- Authentication required for all access
- **Use case:** Internal company wikis

## Wiki Settings

- **Wiki Title:** Displayed in navigation bar
- **Wiki Description:** Meta description for SEO

## File Upload Settings

- **Max Image Size:** 1-100 MB (default: 10 MB)
- **Supported Formats:** PNG, WebP, JPEG

## Maintenance Settings

- **Branch Cleanup Threshold:** 1-365 days (default: 7)
- Inactive draft branches are automatically cleaned up

## GitHub Integration

See [GitHub Setup Guide](github-setup.md)

## Environment Variables

Required in `.env` or system environment:

```env
DJANGO_SECRET_KEY=...          # Django secret key
DJANGO_DEBUG=False             # Never True in production
DJANGO_ALLOWED_HOSTS=...       # Comma-separated domains
DATABASE_URL=...               # Database connection string
REDIS_URL=...                  # Redis connection string
```

Optional:

```env
GITHUB_REMOTE_URL=...          # Git remote URL
GITHUB_SSH_KEY_PATH=...        # Path to SSH private key
GITHUB_WEBHOOK_SECRET=...      # Webhook secret
```

## Database Configuration

Production should use PostgreSQL:

```python
# config/production_settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'gitwiki',
        'USER': 'gitwiki',
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Celery Configuration

Periodic tasks are configured in Django admin:

1. Go to `/admin/django_celery_beat/periodictask/`
2. View/edit periodic tasks:
   - GitHub pull (every 5 minutes)
   - Branch cleanup (daily at 2 AM)
   - Static rebuild (weekly)

## Monitoring

Configure monitoring for:

- Application health (`/admin/`)
- Celery worker status (`celery inspect active`)
- Redis status (`redis-cli ping`)
- Database connections
- Disk space

## Logging

Logs are written to:

- Application: stdout (captured by systemd)
- Nginx: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- Celery: stdout (captured by systemd)

View logs:

```bash
sudo journalctl -u gitwiki -n 100
sudo journalctl -u gitwiki-celery -n 100
```

## Security Recommendations

1. **Use HTTPS:** SSL certificate required
2. **Strong passwords:** Enforce for all users
3. **Regular updates:** Monthly dependency updates
4. **Backup:** Daily automated backups
5. **Monitoring:** Set up alerts for errors
6. **SSH keys:** Protect with proper permissions (600)
```

**3. docs/admin/github-setup.md**
**4. docs/admin/backup-restore.md**
**5. docs/admin/troubleshooting.md**

(Similar detailed guides)

**Deliverable:** Complete admin documentation (5 guides)

---

#### Task 8.3: Developer Documentation (4 hours)

**Create docs/developer/ directory:**

**1. docs/developer/architecture.md**
**2. docs/developer/api.md**
**3. docs/developer/database-schema.md**
**4. docs/developer/testing.md**
**5. docs/developer/contributing.md**

(Detailed technical documentation)

**Deliverable:** Complete developer documentation (5 guides)

---

### Day 10: Deployment Preparation

(Detailed tasks for production settings, scripts, etc.)

### Day 11: UI/UX Polish

(Loading indicators, tooltips, mobile optimization)

### Day 12: Pre-Commit Hooks

(Branch validation, commit message format)

### Days 13-14: Production Deployment

(Deploy, test, go live!)

---

## Success Criteria

Phase 7 is complete when:

- [ ] All 30 dependency vulnerabilities resolved
- [ ] Custom error pages (404, 500, 403) implemented
- [ ] Security audit complete with no critical issues
- [ ] Performance optimized (database indexes, caching, query optimization)
- [ ] 80%+ test coverage achieved
- [ ] Load testing successful (10+ concurrent users)
- [ ] Complete user documentation (5 guides)
- [ ] Complete admin documentation (5 guides)
- [ ] Complete developer documentation (5 guides)
- [ ] Production settings configured
- [ ] Deployment scripts created
- [ ] Pre-commit hooks implemented
- [ ] Production deployment successful
- [ ] All workflows tested in production
- [ ] Monitoring and backups configured
- [ ] Project 100% complete!

---

## Post-Phase 7

After Phase 7 completion:

- ✅ Production-ready wiki system
- ✅ Complete documentation
- ✅ Security audited
- ✅ Performance optimized
- ✅ Ready for users
- 🎉 **Project Complete!**

---

**Good luck with Phase 7! This is the final push to production.** 🚀
