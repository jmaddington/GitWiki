# GitWiki Administrator Guide

Complete guide for GitWiki administrators covering installation, configuration, maintenance, and troubleshooting.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [GitHub Integration](#github-integration)
- [User Management](#user-management)
- [Maintenance](#maintenance)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Installation

### System Requirements

**Minimum Requirements:**
- Python 3.9 or higher
- 2 GB RAM
- 10 GB disk space
- Linux, macOS, or Windows

**Recommended for Production:**
- Python 3.11+
- 4 GB RAM
- 50 GB SSD storage
- Ubuntu 22.04 LTS or similar
- PostgreSQL 14+
- Redis 7+
- Nginx or Apache

### Quick Installation

```bash
# Clone the repository
git clone https://github.com/your-org/gitwiki.git
cd gitwiki

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env file with your settings
nano .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Install Git hooks
./scripts/install-hooks.sh

# Run development server
python manage.py runserver
```

### Production Installation

See the [Deployment Guide](DEPLOYMENT_GUIDE.md) for detailed production setup instructions.

---

## Configuration

### Environment Variables

GitWiki uses environment variables for configuration. Copy `.env.example` to `.env` and configure:

#### Core Settings

```bash
# Secret key - MUST be changed for production
SECRET_KEY=your-secret-key-here

# Debug mode - MUST be False in production
DEBUG=False

# Allowed hosts - comma-separated list
ALLOWED_HOSTS=example.com,www.example.com
```

**Generating a Secret Key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Database Configuration

**PostgreSQL (Recommended for Production):**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/gitwiki
```

**SQLite (Development Only):**
```bash
# Leave DATABASE_URL unset to use SQLite
# Database file: db.sqlite3
```

#### Redis Configuration

```bash
# Redis for caching and Celery
REDIS_URL=redis://localhost:6379/0

# Cache timeout (seconds)
CACHE_TIMEOUT=3600
```

#### GitHub Integration

```bash
# GitHub remote URL for sync
GITHUB_REMOTE_URL=git@github.com:your-org/wiki-content.git

# Auto-sync settings
GITHUB_AUTO_SYNC=True
GITHUB_SYNC_INTERVAL=300  # seconds
```

#### Email Configuration

```bash
# Email settings for notifications
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@example.com

# Admin emails (comma-separated)
ADMIN_EMAILS=admin@example.com,ops@example.com
```

#### Security Settings

```bash
# HTTPS settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS=31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
X_FRAME_OPTIONS=DENY
```

#### Logging Configuration

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log file location
LOG_FILE=/var/log/gitwiki/gitwiki.log

# Log rotation
LOG_MAX_BYTES=10485760  # 10 MB
LOG_BACKUP_COUNT=10
```

#### Sentry Integration (Optional)

```bash
# Sentry DSN for error tracking
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Django Admin Configuration

Access the Django admin interface at `/admin/`:

#### Configuration Settings

Navigate to **Git Service > Configurations** to manage:

**Permission Level:**
- `open`: Anyone can edit without authentication
- `authenticated`: Only authenticated users can edit
- `staff`: Only staff members can edit
- `admin`: Only administrators can edit

**Branch Prefix:**
- Default: `draft`
- Used for draft branch naming: `draft-{user_id}-{uuid}`

**GitHub Settings:**
- Remote URL
- Auto-sync enabled/disabled
- Sync interval
- Last sync time

#### User Management

Navigate to **Authentication > Users**:

1. **Create User:**
   - Click "Add User"
   - Enter username and password
   - Save

2. **Edit Permissions:**
   - Select user
   - Check "Staff status" for Django admin access
   - Check "Superuser status" for full permissions
   - Assign groups if using group-based permissions

3. **Deactivate User:**
   - Uncheck "Active" status
   - User cannot log in but data is preserved

#### Viewing Operations Log

Navigate to **Git Service > Git Operations** to view:
- All Git operations (branch creation, commits, merges)
- User actions
- Success/failure status
- Execution times
- Error messages

Use filters to find specific operations:
- By operation type
- By user
- By date range
- By success status

---

## GitHub Integration

### Setting Up GitHub Sync

**Prerequisites:**
- GitHub repository for wiki content
- SSH key for authentication
- Repository write access

#### Step 1: Generate SSH Key

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "gitwiki@example.com" -f ~/.ssh/gitwiki

# Add public key to GitHub
cat ~/.ssh/gitwiki.pub
# Copy output and add to GitHub: Settings > SSH Keys
```

#### Step 2: Configure SSH

```bash
# Test SSH connection
ssh -T git@github.com

# If connection successful, configure GitWiki
```

#### Step 3: Configure GitWiki

In `.env` file:
```bash
GITHUB_REMOTE_URL=git@github.com:your-org/wiki-content.git
GITHUB_AUTO_SYNC=True
GITHUB_SYNC_INTERVAL=300  # 5 minutes
```

Or via Django admin:
1. Go to **Configurations**
2. Set `github_remote_url`
3. Enable auto-sync if desired

#### Step 4: Test Sync

```bash
# Manual pull test
python manage.py pull_from_github

# Manual push test
python manage.py push_to_github
```

### Sync Behavior

**Auto-Pull:**
- Runs every N seconds (configured interval)
- Pulls latest changes from GitHub
- Regenerates static files if content changed
- Logs all sync operations

**Auto-Push:**
- Can be enabled per-operation
- Pushes after successful merges
- Requires write access to GitHub

**Conflict Handling:**
- Pull conflicts pause auto-sync
- Admin must resolve conflicts manually
- After resolution, auto-sync resumes

### Webhook Integration

For real-time sync, configure GitHub webhook:

1. **In GitHub Repository:**
   - Go to Settings > Webhooks
   - Add webhook
   - Payload URL: `https://your-domain.com/api/git/webhook/`
   - Content type: `application/json`
   - Secret: Configure in `.env` as `WEBHOOK_SECRET`
   - Events: Push events

2. **In GitWiki `.env`:**
   ```bash
   WEBHOOK_SECRET=your-webhook-secret
   ```

3. **Test Webhook:**
   - Push to GitHub
   - Check webhook delivery in GitHub
   - Check GitWiki logs for pull operation

---

## User Management

### Permission Levels

GitWiki uses a simple permission system:

**Permission Levels (from most to least restrictive):**

1. **admin**: Only superusers can edit
2. **staff**: Only staff members can edit
3. **authenticated**: Any logged-in user can edit
4. **open**: Anyone can edit (no authentication required)

**Setting Permission Level:**
```bash
# Via Django admin
Configuration.set_config('permission_level', 'authenticated', 'Who can edit pages')

# Via Django shell
python manage.py shell
>>> from git_service.models import Configuration
>>> Configuration.set_config('permission_level', 'authenticated', 'Permission level')
```

### Creating Users

**Via Django Admin:**
1. Navigate to `/admin/auth/user/`
2. Click "Add User"
3. Enter username and password
4. Click "Save and continue editing"
5. Set permissions:
   - **Active**: User can log in
   - **Staff status**: Access to Django admin
   - **Superuser status**: Full permissions

**Via Command Line:**
```bash
# Create superuser (interactive)
python manage.py createsuperuser

# Create regular user (programmatically)
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_user('username', 'email@example.com', 'password')
>>> user.save()
```

### Managing Edit Sessions

**Viewing Active Sessions:**
1. Navigate to `/editor/sessions/` (requires staff permission)
2. See all active edit sessions
3. View user, file, branch, and last activity

**Force-Closing Sessions:**
```bash
python manage.py shell
>>> from editor.models import EditSession
>>> # Close all sessions for a user
>>> EditSession.objects.filter(user_id=USER_ID).update(is_active=False)
>>> # Close specific session
>>> session = EditSession.objects.get(id=SESSION_ID)
>>> session.mark_inactive()
```

---

## Maintenance

### Routine Maintenance Tasks

#### Daily Tasks

**Check Logs:**
```bash
# Check for errors
tail -f /var/log/gitwiki/gitwiki.log | grep ERROR

# Check sync status
tail -f /var/log/gitwiki/gitwiki.log | grep GITOPS-PULL
```

**Monitor Disk Usage:**
```bash
# Check repository size
du -sh /path/to/wiki_repo

# Check static files size
du -sh /path/to/wiki_static
```

#### Weekly Tasks

**Clean Up Stale Branches:**
```bash
# Clean up draft branches older than 7 days
python manage.py cleanup_stale_branches --age-days 7
```

**Review Active Sessions:**
- Check for abandoned sessions
- Contact users with long-running sessions
- Close sessions if necessary

**Review Git Operations Log:**
- Check for failed operations
- Review error patterns
- Investigate anomalies

#### Monthly Tasks

**Database Maintenance:**
```bash
# PostgreSQL vacuum and analyze
sudo -u postgres psql gitwiki -c "VACUUM ANALYZE;"

# Check database size
sudo -u postgres psql -c "\l+ gitwiki"
```

**Backup Verification:**
- Test backup restoration
- Verify backup integrity
- Update backup procedures if needed

**Security Updates:**
```bash
# Update Python packages
pip install --upgrade -r requirements.txt

# Check for security vulnerabilities
pip check
safety check  # Install: pip install safety
```

#### Quarterly Tasks

**Full Static Rebuild:**
```bash
# Rebuild all static files
python manage.py full_static_rebuild
```

**Performance Review:**
- Check slow query logs
- Review cache hit rates
- Optimize based on usage patterns

**Documentation Review:**
- Update documentation
- Review FAQ based on support tickets
- Update troubleshooting guides

### Database Management

**Backup Database:**
```bash
# PostgreSQL
pg_dump -U postgres gitwiki > backup_$(date +%Y%m%d).sql

# SQLite
sqlite3 db.sqlite3 ".backup backup_$(date +%Y%m%d).sqlite3"
```

**Restore Database:**
```bash
# PostgreSQL
psql -U postgres gitwiki < backup_20251026.sql

# SQLite
cp backup_20251026.sqlite3 db.sqlite3
```

**Migrate Database:**
```bash
# After code updates
python manage.py migrate

# Check migration status
python manage.py showmigrations
```

### Git Repository Management

**Compact Repository:**
```bash
# Navigate to repo
cd /path/to/wiki_repo

# Git garbage collection
git gc --aggressive --prune=now

# Check repo size
du -sh .git/
```

**Check Repository Health:**
```bash
cd /path/to/wiki_repo

# Check for corruption
git fsck --full

# Verify all objects
git verify-pack -v .git/objects/pack/*.idx
```

**Repository Statistics:**
```bash
# Count commits
git rev-list --all --count

# Count branches
git branch -a | wc -l

# Largest files
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sed -n 's/^blob //p' | sort -nk2 | tail -10
```

---

## Monitoring and Logging

### Log Locations

**Application Logs:**
- Location: `/var/log/gitwiki/gitwiki.log` (configured in `.env`)
- Rotation: 10 files × 10 MB (configured)
- Format: ISO timestamp, level, logger, message, [CODE]

**Celery Logs:**
- Location: `/var/log/gitwiki/celery.log`
- Tasks: Background sync, cleanup, rebuilds

**Web Server Logs:**
- Nginx/Apache access logs
- Nginx/Apache error logs

### Grepable Log Codes

All log messages include searchable codes in brackets `[CODE]`. Use these for debugging:

```bash
# Find all security warnings
grep "\[SECURITY-" /var/log/gitwiki/gitwiki.log

# Find Git operation errors
grep "\[GITOPS-.*02\]" /var/log/gitwiki/gitwiki.log

# Find cache operations
grep "\[CACHE-" /var/log/gitwiki/gitwiki.log

# Find editor errors
grep "\[EDITOR-.*ERROR\]" /var/log/gitwiki/gitwiki.log
```

**Common Codes:**
- `SECURITY-*`: Security-related messages
- `GITOPS-*`: Git operations
- `EDITOR-*`: Editor service operations
- `DISPLAY-*`: Display service operations
- `CACHE-*`: Cache operations
- `ERROR-*`: HTTP errors

Full list in `Claude.md` file.

### Monitoring Metrics

**Key Metrics to Monitor:**

1. **Response Time:**
   - Average page load time
   - API endpoint response times
   - Target: < 200ms for pages, < 500ms for search

2. **Error Rate:**
   - HTTP 500 errors
   - Git operation failures
   - Target: < 0.1% error rate

3. **Resource Usage:**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

4. **Repository Metrics:**
   - Repository size
   - Number of branches
   - Number of commits per day
   - Conflict rate

5. **User Activity:**
   - Active users
   - Edit sessions
   - Pages edited per day
   - Search queries

### Setting Up Monitoring

**Using Sentry (Recommended):**

1. Sign up at sentry.io
2. Create a new project
3. Copy the DSN
4. Configure in `.env`:
   ```bash
   SENTRY_DSN=https://your-dsn@sentry.io/project
   SENTRY_ENVIRONMENT=production
   ```

**Using System Monitoring:**

```bash
# Install monitoring tools
sudo apt install prometheus-node-exporter grafana

# Configure Prometheus to scrape metrics
# Configure Grafana dashboards
```

---

## Backup and Recovery

### What to Backup

1. **Git Repository** (most important)
2. **Database** (user accounts, sessions, config)
3. **Static Files** (can be regenerated)
4. **Environment Configuration** (`.env` file)
5. **Uploaded Images** (stored in repository)

### Backup Strategy

**Recommended Backup Schedule:**
- **Hourly**: Git repository (incremental)
- **Daily**: Database full backup
- **Weekly**: Full system backup
- **Monthly**: Off-site backup

### Automated Backup Script

Create `/usr/local/bin/backup-gitwiki.sh`:

```bash
#!/bin/bash

# Configuration
BACKUP_DIR="/backup/gitwiki"
REPO_PATH="/var/gitwiki/wiki_repo"
DB_NAME="gitwiki"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup Git repository
echo "Backing up Git repository..."
tar -czf "$BACKUP_DIR/$DATE/repo.tar.gz" -C "$REPO_PATH" .

# Backup database
echo "Backing up database..."
pg_dump -U postgres "$DB_NAME" | gzip > "$BACKUP_DIR/$DATE/database.sql.gz"

# Backup .env file
echo "Backing up configuration..."
cp /var/gitwiki/.env "$BACKUP_DIR/$DATE/env.backup"

# Clean up old backups (keep 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR/$DATE"
```

**Install Cron Job:**
```bash
# Edit crontab
crontab -e

# Add backup job (runs daily at 2 AM)
0 2 * * * /usr/local/bin/backup-gitwiki.sh >> /var/log/gitwiki-backup.log 2>&1
```

### Recovery Procedures

**Recovering from Git Repository Backup:**
```bash
# Stop GitWiki
sudo systemctl stop gitwiki

# Restore repository
cd /var/gitwiki
rm -rf wiki_repo
mkdir wiki_repo
tar -xzf /backup/gitwiki/20251026_020000/repo.tar.gz -C wiki_repo/

# Regenerate static files
python manage.py full_static_rebuild

# Start GitWiki
sudo systemctl start gitwiki
```

**Recovering from Database Backup:**
```bash
# Stop GitWiki
sudo systemctl stop gitwiki

# Drop and recreate database
sudo -u postgres psql
DROP DATABASE gitwiki;
CREATE DATABASE gitwiki;
\q

# Restore database
gunzip < /backup/gitwiki/20251026_020000/database.sql.gz | psql -U postgres gitwiki

# Start GitWiki
sudo systemctl start gitwiki
```

**Recovering Individual Files:**
```bash
# Use Git history to recover
cd /var/gitwiki/wiki_repo

# Find file in history
git log --all --full-history -- path/to/file.md

# Restore from specific commit
git checkout COMMIT_HASH -- path/to/file.md

# Commit restoration
git commit -m "Restore file.md from COMMIT_HASH"
```

---

## Troubleshooting

### Common Issues

#### Issue: GitWiki Won't Start

**Symptoms:**
- `python manage.py runserver` fails
- Systemd service won't start

**Solutions:**

1. **Check Python environment:**
   ```bash
   which python
   python --version  # Should be 3.9+
   ```

2. **Check dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Check database connection:**
   ```bash
   python manage.py check --database default
   ```

4. **Check logs:**
   ```bash
   tail -100 /var/log/gitwiki/gitwiki.log
   ```

#### Issue: 500 Internal Server Error

**Symptoms:**
- Pages return 500 errors
- "Server Error" page displayed

**Solutions:**

1. **Check logs for error details:**
   ```bash
   grep "\[ERROR-500\]" /var/log/gitwiki/gitwiki.log
   ```

2. **Check DEBUG setting:**
   - Never set `DEBUG=True` in production
   - Use logs instead

3. **Check static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Check permissions:**
   ```bash
   ls -la /var/gitwiki/
   # All files should be readable by web server user
   ```

#### Issue: GitHub Sync Not Working

**Symptoms:**
- Changes not syncing to/from GitHub
- Webhook not triggering pulls

**Solutions:**

1. **Test SSH connection:**
   ```bash
   ssh -T git@github.com
   # Should see: "Hi username! You've successfully authenticated..."
   ```

2. **Check remote URL:**
   ```bash
   cd /var/gitwiki/wiki_repo
   git remote -v
   ```

3. **Manual pull test:**
   ```bash
   python manage.py pull_from_github
   ```

4. **Check Celery worker:**
   ```bash
   sudo systemctl status celery-worker
   # Should be active (running)
   ```

5. **Check webhook secret:**
   - Verify `WEBHOOK_SECRET` in `.env` matches GitHub

#### Issue: Conflicts Not Resolving

**Symptoms:**
- Conflict resolution fails
- Merged content incorrect

**Solutions:**

1. **Check three-way diff:**
   - Verify base, theirs, ours versions
   - Use Git command line to inspect:
   ```bash
   cd /var/gitwiki/wiki_repo
   git checkout BRANCH_NAME
   git show HEAD:path/to/file.md
   ```

2. **Manual conflict resolution:**
   ```bash
   # Checkout branch with conflict
   git checkout draft-123-abc

   # Manually resolve
   nano path/to/file.md

   # Commit resolution
   git add path/to/file.md
   git commit -m "Resolve conflict"

   # Try publish again
   ```

#### Issue: Performance Degradation

**Symptoms:**
- Slow page loads
- High server load
- Search timeouts

**Solutions:**

1. **Check cache status:**
   ```bash
   python manage.py shell
   >>> from django.core.cache import cache
   >>> cache.get('test')  # Test cache connectivity
   ```

2. **Clear cache:**
   ```bash
   python manage.py shell
   >>> from config.cache_utils import clear_all_caches
   >>> clear_all_caches()
   ```

3. **Check Redis:**
   ```bash
   redis-cli ping
   # Should respond: PONG
   ```

4. **Rebuild static files:**
   ```bash
   python manage.py full_static_rebuild
   ```

5. **Check repository size:**
   ```bash
   cd /var/gitwiki/wiki_repo
   git gc --aggressive
   ```

#### Issue: Images Not Displaying

**Symptoms:**
- Uploaded images show broken link
- Image URLs return 404

**Solutions:**

1. **Check image exists in repository:**
   ```bash
   cd /var/gitwiki/wiki_repo
   find . -name "image-name.png"
   ```

2. **Check static files:**
   ```bash
   ls -la /var/gitwiki/wiki_static/main/images/
   ```

3. **Regenerate static files:**
   ```bash
   python manage.py write_branch_to_disk main
   ```

4. **Check web server configuration:**
   - Verify static files are served correctly
   - Check Nginx/Apache configuration

### Getting Help

**Before Seeking Help:**
1. Check this troubleshooting guide
2. Review logs for error messages
3. Search GitHub issues
4. Gather system information:
   ```bash
   python --version
   pip list
   git --version
   uname -a
   ```

**Where to Get Help:**
- GitHub Issues: https://github.com/anthropics/gitwiki/issues
- Documentation: This guide and other docs
- Community Forum: (if available)

---

## Security Best Practices

### Production Security Checklist

- [ ] Change `SECRET_KEY` to a unique random value
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Use HTTPS (set all `SECURE_*` settings)
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HSTS headers
- [ ] Set strong admin passwords
- [ ] Limit admin access to specific IPs (via firewall)
- [ ] Enable Sentry error tracking
- [ ] Regular security updates
- [ ] Regular backups
- [ ] Monitor logs for suspicious activity

### Access Control

**Restrict Django Admin:**
```nginx
# In Nginx config
location /admin {
    allow 192.168.1.0/24;  # Office network
    deny all;
    # ...rest of config
}
```

**Use Strong Passwords:**
```bash
# Generate strong password
openssl rand -base64 32
```

**Enable Two-Factor Authentication:**
- Install: `pip install django-otp`
- Configure per Django OTP documentation

### Regular Security Audits

**Monthly Security Tasks:**
```bash
# Check for outdated packages
pip list --outdated

# Security vulnerability scan
safety check

# Check for exposed secrets
grep -r "SECRET_KEY\|password\|PASSWORD" .env

# Review user accounts
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(is_superuser=True)
```

**Security Monitoring:**
- Review failed login attempts
- Monitor unusual activity patterns
- Check for unauthorized admin access
- Review Git operation logs

---

*For deployment procedures, see [Deployment Guide](DEPLOYMENT_GUIDE.md). For development information, see [Developer Guide](../developer/DEVELOPER_GUIDE.md).*
