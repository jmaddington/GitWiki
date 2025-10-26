# GitWiki Production Deployment Files

This directory contains production-ready configuration files for deploying GitWiki.

## Directory Structure

```
deployment/
├── nginx/
│   └── gitwiki.conf          # Nginx reverse proxy configuration
├── systemd/
│   ├── gitwiki.service       # Main application service
│   ├── celery-worker.service # Celery worker service
│   └── celery-beat.service   # Celery beat scheduler service
└── README.md                 # This file
```

## Nginx Configuration

### Installation

```bash
# Copy nginx configuration
sudo cp deployment/nginx/gitwiki.conf /etc/nginx/sites-available/gitwiki

# Edit the configuration
sudo nano /etc/nginx/sites-available/gitwiki

# Update these values:
# - server_name: Your domain (example.com)
# - ssl_certificate paths: Your SSL certificate paths
# - Paths to static files

# Enable the site
sudo ln -s /etc/nginx/sites-available/gitwiki /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Features

- **SSL/TLS Configuration**: Mozilla Intermediate compatibility
- **Security Headers**: HSTS, X-Frame-Options, CSP, etc.
- **Rate Limiting**: Protects API and login endpoints
- **Static File Caching**: Optimized cache headers
- **Gzip Compression**: Reduces bandwidth usage
- **Health Check Support**: No logging for health endpoints
- **OCSP Stapling**: Improved SSL performance

## Systemd Services

### Installation

```bash
# Copy service files
sudo cp deployment/systemd/*.service /etc/systemd/system/

# Edit service files if needed
# Update paths and user/group if different
sudo nano /etc/systemd/system/gitwiki.service
sudo nano /etc/systemd/system/celery-worker.service
sudo nano /etc/systemd/system/celery-beat.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable gitwiki celery-worker celery-beat

# Start services
sudo systemctl start gitwiki
sudo systemctl start celery-worker
sudo systemctl start celery-beat

# Check status
sudo systemctl status gitwiki
sudo systemctl status celery-worker
sudo systemctl status celery-beat
```

### Service Management

```bash
# Start services
sudo systemctl start gitwiki celery-worker celery-beat

# Stop services
sudo systemctl stop gitwiki celery-worker celery-beat

# Restart services
sudo systemctl restart gitwiki celery-worker celery-beat

# Reload Gunicorn (graceful restart)
sudo systemctl reload gitwiki

# View logs
sudo journalctl -u gitwiki -f
sudo journalctl -u celery-worker -f
sudo journalctl -u celery-beat -f

# Check service health
sudo systemctl is-active gitwiki
sudo systemctl is-enabled gitwiki
```

### Service Features

**gitwiki.service:**
- Runs Gunicorn with 4 workers
- Graceful reload support
- Security hardening (NoNewPrivileges, PrivateDevices, etc.)
- Auto-restart on failure
- Proper dependency management

**celery-worker.service:**
- 4 concurrent workers
- Max 1000 tasks per child (prevents memory leaks)
- Auto-restart on failure
- Proper shutdown handling (600s timeout)

**celery-beat.service:**
- Scheduled task coordinator
- Depends on celery-worker
- Persistent schedule database

## Pre-Deployment Checklist

Before deploying, ensure:

- [ ] PostgreSQL installed and configured
- [ ] Redis installed and running
- [ ] User `gitwiki` created
- [ ] Application installed in `/home/gitwiki/app`
- [ ] Virtual environment created and activated
- [ ] Dependencies installed from requirements-production.txt
- [ ] `.env` file configured with production settings
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Migrations applied: `python manage.py migrate`
- [ ] Superuser created: `python manage.py createsuperuser`
- [ ] Log directory created: `/home/gitwiki/logs`
- [ ] Wiki directories created: `/home/gitwiki/wiki_repo`, `/home/gitwiki/wiki_static`
- [ ] Permissions set correctly (gitwiki user owns all files)
- [ ] Firewall configured (allow 80, 443)
- [ ] SSL certificate obtained (Let's Encrypt)

## Post-Deployment Verification

```bash
# Test application
curl http://localhost:8000/health/

# Test through Nginx (if SSL configured)
curl https://yourdomain.com/health/

# Check service status
sudo systemctl status gitwiki celery-worker celery-beat

# Check logs for errors
sudo journalctl -u gitwiki -n 50 --no-pager
tail -f /home/gitwiki/logs/gunicorn-error.log

# Verify database connection
python manage.py dbshell

# Test admin access
# Visit: https://yourdomain.com/admin/
```

## Monitoring

### Health Endpoints

- `/health/` - Full health check (database, cache, repository)
- `/ready/` - Readiness probe (lightweight)
- `/alive/` - Liveness probe (minimal)

### Logs

Application logs:
- `/home/gitwiki/logs/gitwiki.log` - Django application log
- `/home/gitwiki/logs/gunicorn-access.log` - HTTP access log
- `/home/gitwiki/logs/gunicorn-error.log` - Gunicorn errors
- `/home/gitwiki/logs/celery-worker.log` - Celery worker log
- `/home/gitwiki/logs/celery-beat.log` - Celery beat log

System logs:
- `sudo journalctl -u gitwiki` - Systemd logs for main app
- `sudo journalctl -u celery-worker` - Systemd logs for worker
- `sudo journalctl -u celery-beat` - Systemd logs for beat

Nginx logs:
- `/var/log/nginx/gitwiki-access.log` - Nginx access log
- `/var/log/nginx/gitwiki-error.log` - Nginx error log

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status gitwiki

# View full logs
sudo journalctl -u gitwiki -xe

# Check configuration
/home/gitwiki/app/venv/bin/gunicorn --check-config -c /home/gitwiki/app/gunicorn_config.py

# Verify environment file
cat /home/gitwiki/app/.env
```

### High Memory Usage

```bash
# Check process memory
ps aux | grep gunicorn | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Reduce workers in gitwiki.service
sudo nano /etc/systemd/system/gitwiki.service
# Change --workers to 2 or 3

# Restart
sudo systemctl daemon-reload
sudo systemctl restart gitwiki
```

### Slow Response Times

```bash
# Check worker status
pstree -p $(pgrep gunicorn | head -1)

# Enable Django Debug Toolbar in staging
# Check slow queries in logs

# Verify cache is working
redis-cli ping
redis-cli info stats
```

## Security Notes

- All services run as non-root user `gitwiki`
- Services use `NoNewPrivileges` and `PrivateDevices`
- File system access is restricted with `ProtectSystem` and `ProtectHome`
- Nginx includes security headers (HSTS, CSP, X-Frame-Options)
- Rate limiting protects against abuse
- SSL/TLS configuration follows Mozilla guidelines

## Backup

See `/scripts/backup-gitwiki.sh` for automated backup script.

Schedule with cron:
```bash
sudo crontab -e
# Add: 0 2 * * * /home/gitwiki/app/scripts/backup-gitwiki.sh /backup/gitwiki >> /var/log/gitwiki-backup.log 2>&1
```

## Updates

```bash
# Stop services
sudo systemctl stop gitwiki celery-worker celery-beat

# Update code
cd /home/gitwiki/app
git pull

# Activate virtualenv
source venv/bin/activate

# Update dependencies
pip install -r requirements-production.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start services
sudo systemctl start gitwiki celery-worker celery-beat

# Verify
curl http://localhost:8000/health/
```

## Additional Resources

- [Admin Guide](../docs/admin/ADMIN_GUIDE.md) - Complete administration documentation
- [Deployment Guide](../docs/admin/DEPLOYMENT_GUIDE.md) - Detailed deployment procedures
- [Developer Guide](../docs/developer/DEVELOPER_GUIDE.md) - Development documentation

## Support

For issues or questions:
1. Check the logs (systemd, gunicorn, celery, nginx)
2. Review the troubleshooting guides
3. Consult the documentation
4. Open an issue on GitHub
