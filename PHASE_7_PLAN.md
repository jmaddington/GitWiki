# Phase 7 Implementation Plan - Polish & Deployment

**Created:** October 26, 2025
**Status:** Ready to Implement
**Duration:** 2-3 weeks (10-14 days)
**Priority:** CRITICAL - Final phase to production

---

## Executive Summary

Phase 7 is the final phase of GitWiki MVP development, focusing on production readiness through security hardening, performance optimization, comprehensive testing, and complete documentation. This phase transforms GitWiki from a feature-complete application into a production-ready system.

**Critical Issues to Address:**
- ⚠️ **Security:** Hardcoded SECRET_KEY and DEBUG=True in settings.py
- ⚠️ **Error Handling:** No custom error pages (404, 500, 403)
- ⚠️ **Test Coverage:** Display and Editor apps have minimal tests
- ⚠️ **Documentation:** No user/admin guides
- ⚠️ **Production Config:** No production settings file

---

## Week 1: Security & Error Handling (Days 1-5)

### Day 1-2: Security Hardening - CRITICAL ⚠️

**Priority:** Highest - Blocks production deployment

**Current Security Issues:**
```python
# config/settings.py - CURRENT STATE (INSECURE)
SECRET_KEY = "django-insecure-3@gchapvnnjn*^+s)v9^#x5l%4^i8_^tau&45*ian1jz914cn!"
DEBUG = True
ALLOWED_HOSTS = []
```

**Tasks:**

1. **Create Environment-Based Configuration**
   ```bash
   # Create .env.example file
   touch .env.example
   ```

   Add to .env.example:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   DATABASE_URL=sqlite:///db.sqlite3  # or postgresql://...
   REDIS_URL=redis://localhost:6379/0
   CELERY_BROKER_URL=redis://localhost:6379/0
   ```

2. **Install python-decouple**
   ```bash
   pip install python-decouple
   echo "python-decouple==3.8" >> requirements.txt
   ```

3. **Update config/settings.py**
   ```python
   from decouple import config, Csv

   # SECURITY WARNING: keep the secret key used in production secret!
   SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only')

   # SECURITY WARNING: don't run with debug turned on in production!
   DEBUG = config('DEBUG', default=True, cast=bool)

   ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
   ```

4. **Create config/settings_production.py**
   - Import from base settings.py
   - Override DEBUG = False
   - Add security headers
   - Configure HTTPS settings
   - See code example below

5. **Security Headers**
   ```python
   # config/settings_production.py
   SECURE_SSL_REDIRECT = True
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   SECURE_BROWSER_XSS_FILTER = True
   SECURE_CONTENT_TYPE_NOSNIFF = True
   X_FRAME_OPTIONS = 'DENY'
   SECURE_HSTS_SECONDS = 31536000  # 1 year
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   ```

6. **Update .gitignore**
   ```
   .env
   *.env
   .env.local
   ```

**Testing:**
- Test with DEBUG=False locally
- Verify SECRET_KEY is read from environment
- Test with ALLOWED_HOSTS restrictions
- Verify security headers in response

**Grepable Codes to Add:**
- SECURITY-01: Secret key loaded from environment
- SECURITY-02: Production mode enabled
- SECURITY-03: Security headers configured

---

### Day 3: Custom Error Pages

**Priority:** High - Improves user experience

**Current Issue:** Default Django error pages are shown (ugly, expose information)

**Tasks:**

1. **Create templates/errors/ directory**
   ```bash
   mkdir -p templates/errors
   ```

2. **Create templates/errors/404.html** (Page Not Found)
   ```html
   {% extends "display/base.html" %}

   {% block content %}
   <div class="container mt-5 text-center">
     <h1 class="display-1">404</h1>
     <h2>Page Not Found</h2>
     <p class="lead">The page you're looking for doesn't exist.</p>
     <div class="mt-4">
       <a href="/" class="btn btn-primary">Go Home</a>
       <a href="/search/" class="btn btn-outline-secondary">Search</a>
     </div>
   </div>
   {% endblock %}
   ```

3. **Create templates/errors/500.html** (Server Error)
   - No dynamic content (may fail during rendering)
   - Static HTML with inline CSS
   - Simple, helpful message
   - Link back to home

4. **Create templates/errors/403.html** (Permission Denied)
   - Explain permission issue
   - Suggest logging in
   - Link to login page

5. **Configure in config/settings.py**
   ```python
   TEMPLATES = [
       {
           'DIRS': [
               BASE_DIR / 'templates',
               BASE_DIR / 'templates/errors',
           ],
           ...
       }
   ]
   ```

6. **Add error handlers in config/urls.py**
   ```python
   handler404 = 'display.views.custom_404'
   handler500 = 'display.views.custom_500'
   handler403 = 'display.views.custom_403'
   ```

7. **Create view functions in display/views.py**
   ```python
   def custom_404(request, exception):
       return render(request, 'errors/404.html', status=404)

   def custom_500(request):
       return render(request, 'errors/500.html', status=500)

   def custom_403(request, exception):
       return render(request, 'errors/403.html', status=403)
   ```

**Testing:**
- Test 404 by accessing non-existent page
- Test 403 by accessing restricted page
- Test 500 by triggering error (temporarily)

**Grepable Codes to Add:**
- ERROR-404: Page not found
- ERROR-500: Server error occurred
- ERROR-403: Permission denied

---

### Day 4: Error Handling Audit

**Priority:** High - Improves reliability

**Tasks:**

1. **Review All API Endpoints**
   - Check git_service/api.py (5 endpoints)
   - Check editor/api.py (6 endpoints)
   - Ensure consistent error responses
   - Add try/except where missing

2. **Standard Error Response Format**
   ```python
   # Example for REST API endpoints
   {
       "success": false,
       "error": {
           "code": "GITOPS-COMMIT02",
           "message": "Failed to commit changes",
           "details": "Branch does not exist"
       }
   }
   ```

3. **Add Transaction Rollback**
   ```python
   from django.db import transaction

   @transaction.atomic
   def publish_edit(request):
       # All database operations here will rollback on error
       ...
   ```

4. **Improve User-Facing Error Messages**
   - Replace technical errors with user-friendly messages
   - Add suggestions for fixing errors
   - Maintain detailed logging for debugging

5. **Test Edge Cases**
   - Empty file paths
   - Invalid branch names
   - Missing files
   - Large file uploads
   - Concurrent operations

**Deliverables:**
- Consistent error handling across all endpoints
- User-friendly error messages
- Detailed error logging

---

### Day 5: Pre-commit Hooks

**Priority:** Medium - Improves code quality

**Tasks:**

1. **Create .githooks/pre-commit** script
   ```bash
   #!/bin/bash
   # Pre-commit hook for GitWiki
   # Validates branch naming and prevents direct commits to main

   branch=$(git symbolic-ref --short HEAD)

   # Block direct commits to main
   if [[ $branch == "main" ]]; then
     echo "❌ Error: Direct commits to main are not allowed"
     echo "Please create a draft branch and publish through the web UI"
     exit 1
   fi

   # Validate draft branch naming
   if [[ $branch == draft-* ]]; then
     if [[ ! $branch =~ ^draft-[0-9]+-[a-z0-9]{6,8}$ ]]; then
       echo "❌ Error: Invalid draft branch name: $branch"
       echo "Format must be: draft-{user_id}-{uuid}"
       exit 1
     fi
   fi

   echo "✅ Pre-commit checks passed"
   exit 0
   ```

2. **Make executable**
   ```bash
   chmod +x .githooks/pre-commit
   ```

3. **Create installation script**
   ```bash
   # scripts/install-hooks.sh
   #!/bin/bash
   cp .githooks/pre-commit .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   echo "✅ Git hooks installed successfully"
   ```

4. **Add to README.md**
   - Installation instructions
   - What the hooks do
   - How to bypass (if needed)

---

## Week 2: Performance, Testing & Documentation (Days 6-10)

### Day 6-7: Performance Optimization

**Priority:** Medium-High - Improves user experience

**Tasks:**

1. **Add Database Indexes**
   ```python
   # git_service/models.py
   class EditSession(models.Model):
       class Meta:
           indexes = [
               models.Index(fields=['user', 'is_active']),
               models.Index(fields=['created_at']),
               models.Index(fields=['last_modified']),
           ]

   # Create migration
   python manage.py makemigrations
   ```

2. **Cache Static File Metadata**
   ```python
   # display/views.py
   from django.core.cache import cache

   def get_page_metadata(file_path):
       cache_key = f'metadata:{file_path}'
       metadata = cache.get(cache_key)
       if metadata is None:
           metadata = load_metadata(file_path)
           cache.set(cache_key, metadata, timeout=3600)  # 1 hour
       return metadata
   ```

3. **Optimize Markdown Rendering**
   - Cache compiled HTML
   - Only regenerate when file changes
   - Use markdown render cache

4. **Profile Slow Endpoints**
   ```python
   # Use Django Debug Toolbar in development
   pip install django-debug-toolbar

   # Or manual profiling
   import cProfile
   ```

5. **Add Pagination to Large Lists**
   - Paginate search results (already done)
   - Paginate file listings
   - Paginate history views

6. **Optimize Conflict Detection**
   - Current: 2-minute cache (good)
   - Add: Invalidate cache on new commits
   - Add: Background cache warming

**Benchmarks to Achieve:**
- Page load: < 200ms
- Search: < 500ms
- Conflict detection: < 2s for 20 branches
- Static generation: < 10s for 100 pages

---

### Day 8: Test Coverage Improvement

**Priority:** High - Critical for production confidence

**Current Coverage:**
- git_service: Good (545 lines of tests)
- config: Good (303 lines of tests)
- display: Minimal (3 lines)
- editor: Minimal (3 lines)

**Target:** 80%+ overall coverage

**Tasks:**

1. **Install Coverage Tool**
   ```bash
   pip install coverage
   echo "coverage==7.3.2" >> requirements.txt
   ```

2. **Add Display App Tests** (display/tests.py)
   ```python
   class DisplayTestCase(TestCase):
       def test_wiki_home_renders(self):
           # Test home page

       def test_wiki_page_renders(self):
           # Test individual page

       def test_search_functionality(self):
           # Test search

       def test_page_history(self):
           # Test history display

       def test_404_on_missing_page(self):
           # Test 404 error
   ```

3. **Add Editor App Tests** (editor/tests.py)
   ```python
   class EditorTestCase(TestCase):
       def test_start_edit_creates_session(self):
           # Test session creation

       def test_save_draft_updates_session(self):
           # Test save

       def test_commit_draft_creates_commit(self):
           # Test commit

       def test_publish_merges_to_main(self):
           # Test publish

       def test_image_upload(self):
           # Test image upload
   ```

4. **Integration Tests** (create integration_tests.py)
   - Complete edit workflow (start → save → commit → publish)
   - Conflict workflow (two users editing same file)
   - Image upload workflow
   - Search workflow

5. **Load Testing** (separate script)
   ```bash
   # Use locust or similar
   pip install locust

   # Create locustfile.py for concurrent user simulation
   ```

6. **Run Coverage Report**
   ```bash
   coverage run manage.py test
   coverage report
   coverage html
   # Open htmlcov/index.html to see report
   ```

**Target Coverage by App:**
- git_service: 85%+
- editor: 80%+
- display: 80%+
- config: 85%+
- Overall: 80%+

---

### Day 9-10: Documentation

**Priority:** High - Critical for handoff and maintenance

**Tasks:**

**Day 9: User & Admin Guides**

1. **Create docs/ directory**
   ```bash
   mkdir -p docs/{user,admin,developer}
   ```

2. **USER_GUIDE.md** (docs/user/USER_GUIDE.md)
   ```markdown
   # GitWiki User Guide

   ## Getting Started
   - Viewing pages
   - Navigation
   - Search

   ## Editing Pages
   - Starting an edit
   - Markdown syntax
   - Auto-save
   - Committing changes
   - Publishing

   ## Working with Images
   - File upload
   - Drag and drop
   - Clipboard paste (Ctrl+V)

   ## Conflict Resolution
   - What are conflicts?
   - Resolving text conflicts
   - Resolving image conflicts

   ## FAQ
   ```

3. **ADMIN_GUIDE.md** (docs/admin/ADMIN_GUIDE.md)
   ```markdown
   # GitWiki Admin Guide

   ## Installation
   - Prerequisites
   - Installation steps
   - Initial configuration

   ## Configuration
   - Permission modes
   - Wiki settings
   - File upload settings
   - GitHub integration

   ## GitHub Setup
   - Creating SSH keys
   - Configuring webhooks
   - Testing connection

   ## Maintenance
   - Branch cleanup
   - Static file regeneration
   - Backups
   - Monitoring

   ## Troubleshooting
   - Common issues
   - Logs location
   - Support resources
   ```

**Day 10: Developer Guide & Cleanup**

4. **DEVELOPER_GUIDE.md** (docs/developer/DEVELOPER_GUIDE.md)
   ```markdown
   # GitWiki Developer Guide

   ## Architecture
   - System overview
   - Django apps structure
   - Data models

   ## API Reference
   - Git Service API
   - Editor Service API
   - Display Service API

   ## Development Setup
   - Prerequisites
   - Installation
   - Running tests

   ## Testing
   - Running tests
   - Writing tests
   - Coverage

   ## Contributing
   - Code style
   - Commit guidelines
   - Pull request process

   ## AIDEV-NOTE Index
   - All anchor locations
   - Usage guidelines
   ```

5. **DEPLOYMENT_GUIDE.md** (docs/admin/DEPLOYMENT_GUIDE.md)
   ```markdown
   # GitWiki Deployment Guide

   ## Production Settings
   - Environment variables
   - Security settings
   - Database configuration

   ## Deployment Options
   - Docker deployment
   - Traditional server deployment
   - Cloud platforms (AWS, DigitalOcean, etc.)

   ## Web Server Configuration
   - Nginx example
   - Apache example
   - SSL/TLS setup

   ## Process Management
   - Systemd service files
   - Supervisor configuration
   - Celery worker management

   ## Monitoring & Logging
   - Health checks
   - Log aggregation
   - Performance monitoring
   - Error tracking

   ## Backups
   - Database backups
   - Git repository backups
   - Configuration backups
   ```

6. **Clean Up Documentation**
   - Remove outdated files
   - Consolidate information
   - Update README.md with links to new guides
   - Remove PHASE_* summaries (keep in git history)

**Deliverables:**
- Complete user guide
- Complete admin guide
- Complete developer guide
- Complete deployment guide
- Updated README.md
- Clean documentation structure

---

## Week 3 (Optional): Deployment Preparation (Days 11-14)

### Day 11: Production Configuration

**Tasks:**

1. **Create config/settings_production.py**
   - Import from settings.py
   - Override DEBUG, ALLOWED_HOSTS
   - Configure databases for production
   - Add security headers
   - Configure static files
   - Configure media files

2. **Create requirements-production.txt**
   ```
   # Pin all versions
   Django==4.2.7
   djangorestframework==3.14.0
   GitPython==3.1.40
   celery==5.3.4
   redis==5.0.1
   django-celery-beat==2.5.0
   django-redis==5.4.0
   python-decouple==3.8
   gunicorn==21.2.0
   markdown==3.5.1
   Pygments==2.17.2
   ```

3. **Create .env.example**
   - All environment variables documented
   - Example values provided
   - Comments explaining each setting

4. **Create Docker configuration** (optional)
   ```dockerfile
   # Dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements-production.txt .
   RUN pip install -r requirements-production.txt

   COPY . .

   CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
   ```

5. **Create docker-compose.yml** (optional)
   - Django app
   - PostgreSQL
   - Redis
   - Celery worker
   - Celery beat

---

### Day 12: Monitoring & Logging

**Tasks:**

1. **Create Health Check Endpoint**
   ```python
   # config/urls.py
   path('health/', views.health_check, name='health_check'),

   # config/views.py
   def health_check(request):
       # Check database
       # Check Redis
       # Check disk space
       # Return status
       return JsonResponse({'status': 'healthy'})
   ```

2. **Configure Logging**
   ```python
   # config/settings_production.py
   LOGGING = {
       'version': 1,
       'disable_existing_loggers': False,
       'formatters': {
           'verbose': {
               'format': '{levelname} {asctime} {module} {message} [{extra_code}]',
               'style': '{',
           },
       },
       'handlers': {
           'file': {
               'level': 'INFO',
               'class': 'logging.handlers.RotatingFileHandler',
               'filename': '/var/log/gitwiki/gitwiki.log',
               'maxBytes': 10485760,  # 10MB
               'backupCount': 10,
               'formatter': 'verbose',
           },
       },
       'root': {
           'handlers': ['file'],
           'level': 'INFO',
       },
   }
   ```

3. **Add Sentry Integration** (optional)
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.django import DjangoIntegration

   sentry_sdk.init(
       dsn=config('SENTRY_DSN', default=''),
       integrations=[DjangoIntegration()],
       environment=config('ENVIRONMENT', default='production'),
   )
   ```

4. **Create Backup Scripts**
   ```bash
   # scripts/backup-database.sh
   # scripts/backup-repo.sh
   # scripts/backup-config.sh
   ```

---

### Day 13-14: Deployment & Testing

**Tasks:**

1. **Deploy to Staging**
   - Set up staging server
   - Deploy code
   - Run migrations
   - Test thoroughly

2. **Security Audit on Staging**
   - Run security scanners
   - Test authentication
   - Test permissions
   - Review logs

3. **Performance Testing on Staging**
   - Load testing
   - Stress testing
   - Monitor resource usage

4. **Fix Issues Found**
   - Address security issues
   - Fix performance bottlenecks
   - Improve error handling

5. **Deploy to Production**
   - Follow deployment guide
   - Monitor closely for 48 hours
   - Be ready to rollback if needed

---

## Success Criteria

**Before Marking Phase 7 Complete:**

- [ ] SECRET_KEY moved to environment variable
- [ ] DEBUG disabled in production
- [ ] ALLOWED_HOSTS configured
- [ ] Security headers enabled
- [ ] Custom 404, 500, 403 pages
- [ ] Consistent error handling across all endpoints
- [ ] Pre-commit hooks created and documented
- [ ] Database indexes added
- [ ] Caching implemented
- [ ] 80%+ test coverage achieved
- [ ] User guide complete
- [ ] Admin guide complete
- [ ] Developer guide complete
- [ ] Deployment guide complete
- [ ] Production settings file created
- [ ] Requirements pinned
- [ ] Health check endpoint working
- [ ] Logging configured
- [ ] Backup procedures documented
- [ ] Successfully deployed to staging
- [ ] Security audit passed
- [ ] Performance benchmarks met

---

## Code Review Checklist

**Self-Review Questions:**

1. **Security:**
   - Are all secrets in environment variables?
   - Is DEBUG=False in production?
   - Are security headers enabled?
   - Is HTTPS enforced?

2. **Error Handling:**
   - Are all errors handled gracefully?
   - Are error messages user-friendly?
   - Is detailed logging available for debugging?
   - Do custom error pages work?

3. **Performance:**
   - Are database queries optimized?
   - Is caching implemented?
   - Are indexes in place?
   - Do pages load quickly?

4. **Testing:**
   - Is coverage above 80%?
   - Are all critical paths tested?
   - Do integration tests pass?
   - Has load testing been done?

5. **Documentation:**
   - Can a new user understand how to use the system?
   - Can an admin deploy and configure the system?
   - Can a developer understand and extend the code?
   - Are all features documented?

6. **Production Readiness:**
   - Can the system be deployed?
   - Is monitoring in place?
   - Are backups configured?
   - Is there a rollback plan?

---

## Advice for Implementation

**What Would I Tell Another Developer:**

1. **Start with Security** - Don't skip this. Production deployment without security is dangerous.

2. **Test as You Go** - Don't leave all testing for Day 8. Write tests alongside fixes.

3. **Documentation is Critical** - Future you (or other developers) will thank you for good docs.

4. **Don't Over-Optimize** - Focus on obvious wins (indexes, caching). Don't spend days on micro-optimizations.

5. **Use .env.example** - Make it easy for others to configure the system.

6. **Test Error Pages with DEBUG=False** - They won't work with DEBUG=True.

7. **Monitor Staging Closely** - Staging should reveal issues before production.

8. **Keep Changelogs** - Document what changes in each deployment.

9. **Have a Rollback Plan** - Know how to quickly revert if something goes wrong.

10. **Don't Rush Deployment** - Better to be slow and safe than fast and broken.

---

## Files to Create/Modify

**New Files:**
- .env.example
- config/settings_production.py
- templates/errors/404.html
- templates/errors/500.html
- templates/errors/403.html
- .githooks/pre-commit
- scripts/install-hooks.sh
- docs/user/USER_GUIDE.md
- docs/admin/ADMIN_GUIDE.md
- docs/admin/DEPLOYMENT_GUIDE.md
- docs/developer/DEVELOPER_GUIDE.md
- scripts/backup-database.sh
- scripts/backup-repo.sh
- Dockerfile (optional)
- docker-compose.yml (optional)

**Modified Files:**
- config/settings.py (environment variables)
- config/urls.py (error handlers)
- display/views.py (error view functions, caching)
- git_service/models.py (indexes)
- editor/models.py (indexes)
- requirements.txt (new dependencies)
- README.md (links to guides)
- .gitignore (.env files)
- display/tests.py (comprehensive tests)
- editor/tests.py (comprehensive tests)

**Files to Remove:**
- PROJECT_REVIEW_2025-10-25.md (outdated, keep in git history)

---

## Estimated Time Breakdown

| Task | Days | Priority |
|------|------|----------|
| Security Hardening | 2 | Critical |
| Error Pages | 1 | High |
| Error Handling Audit | 1 | High |
| Pre-commit Hooks | 1 | Medium |
| Performance Optimization | 2 | Medium-High |
| Test Coverage | 1 | High |
| Documentation | 2 | High |
| Production Config | 1 | Medium |
| Monitoring & Logging | 1 | Medium |
| Deployment & Testing | 2 | High |
| **Total** | **14 days** | - |

**Minimum Viable:** Days 1-10 (security, errors, testing, docs)
**Recommended:** Days 1-12 (add production config and monitoring)
**Comprehensive:** Days 1-14 (full deployment)

---

## Next Steps After Phase 7

**Post-MVP Enhancements (Future Phases):**

1. **Mermaid Diagram Support**
2. **Advanced Permission System** (page-level, roles)
3. **Git LFS Support** (large files)
4. **Real-time Collaborative Editing**
5. **Email Notifications**
6. **Export Functionality** (PDF, static site)
7. **Analytics Dashboard**
8. **Mobile App**
9. **API for External Tools**
10. **Advanced Search** (PostgreSQL full-text)

---

## Resources

**Security:**
- Django Security Checklist: https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
- OWASP Top 10: https://owasp.org/www-project-top-ten/

**Testing:**
- Django Testing: https://docs.djangoproject.com/en/4.2/topics/testing/
- Coverage.py: https://coverage.readthedocs.io/

**Deployment:**
- Django Deployment: https://docs.djangoproject.com/en/4.2/howto/deployment/
- Gunicorn: https://docs.gunicorn.org/
- Nginx: https://nginx.org/en/docs/

**Monitoring:**
- Sentry: https://docs.sentry.io/
- Django Logging: https://docs.djangoproject.com/en/4.2/topics/logging/

---

*Created: October 26, 2025*
*Status: Ready to Implement*
*Priority: Critical - Final phase to production*
