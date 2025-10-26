# GitWiki Deployment Guide

Complete guide for deploying GitWiki to production environments.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Production Requirements](#production-requirements)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Deployment Options](#deployment-options)
- [Manual Deployment to Ubuntu](#manual-deployment-to-ubuntu)
- [Docker Deployment](#docker-deployment)
- [Web Server Configuration](#web-server-configuration)
- [SSL/HTTPS Configuration](#sslhttps-configuration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Post-Deployment](#post-deployment)
- [Troubleshooting Deployment Issues](#troubleshooting-deployment-issues)

---

## Deployment Overview

### Architecture

Production GitWiki deployment consists of:

```
Internet
    ↓
SSL Termination (Let's Encrypt)
    ↓
Reverse Proxy (Nginx)
    ↓
WSGI Server (Gunicorn)
    ↓
Django Application (GitWiki)
    ↓
├── PostgreSQL Database
├── Redis Cache/Queue
└── Git Repository
    ↓
Celery Workers (Background tasks)
```

### Deployment Timeline

Estimated time: 2-4 hours for first deployment

- Setup: 30-60 minutes
- Configuration: 30-60 minutes
- Testing: 30-60 minutes
- Optimization: 30-60 minutes

---

## Production Requirements

### Server Requirements

**Minimum Production Server:**
- 2 CPU cores
- 4 GB RAM
- 50 GB SSD storage
- Ubuntu 22.04 LTS (or similar)
- Public IP address
- Domain name configured

**Recommended Production Server:**
- 4 CPU cores
- 8 GB RAM
- 100 GB SSD storage
- Ubuntu 22.04 LTS
- Public IP with DDoS protection
- Domain name with DNS configured

### Software Requirements

```bash
# System packages
- Python 3.11
- PostgreSQL 14+
- Redis 7+
- Nginx 1.22+
- Git 2.34+
- Certbot (Let's Encrypt)

# Python packages
- See requirements.txt
```

### Network Requirements

**Ports:**
- 80 (HTTP) - for Let's Encrypt verification
- 443 (HTTPS) - for production traffic
- 22 (SSH) - for server administration

**DNS:**
- A record pointing to server IP
- Optional: CNAME for www subdomain

---

## Pre-Deployment Checklist

### Before You Begin

- [ ] Server provisioned and accessible via SSH
- [ ] Domain name configured with DNS
- [ ] SSL certificate strategy decided
- [ ] Database backup strategy planned
- [ ] Monitoring solution selected
- [ ] Emergency contact information ready

### Security Checklist

- [ ] Strong passwords generated
- [ ] SSH keys configured
- [ ] Firewall rules planned
- [ ] Secret key generated
- [ ] Environment variables prepared
- [ ] Backup system tested

### Documentation Checklist

- [ ] Deployment notes template ready
- [ ] Contact information documented
- [ ] Emergency procedures documented
- [ ] Backup procedures documented

---

## Deployment Options

### Option 1: Manual Deployment to Ubuntu

**Best For:**
- Full control over configuration
- Understanding the deployment process
- Custom requirements

**Advantages:**
- Maximum flexibility
- Direct troubleshooting
- Performance optimization

**Disadvantages:**
- More complex initial setup
- Manual updates required

→ See [Manual Deployment to Ubuntu](#manual-deployment-to-ubuntu) below

### Option 2: Docker Deployment

**Best For:**
- Quick deployment
- Consistent environments
- Easy scaling

**Advantages:**
- Faster setup
- Easier updates
- Portable configuration

**Disadvantages:**
- Additional layer of abstraction
- Resource overhead

→ See [Docker Deployment](#docker-deployment) below

### Option 3: Platform as a Service (PaaS)

**Options:**
- Heroku
- Railway
- DigitalOcean App Platform
- AWS Elastic Beanstalk

**Advantages:**
- Simplest deployment
- Managed infrastructure
- Auto-scaling

**Disadvantages:**
- Higher cost
- Less control
- Platform lock-in

*Note: PaaS deployment guides available in community documentation.*

---

## Manual Deployment to Ubuntu

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    git \
    build-essential \
    libpq-dev \
    certbot python3-certbot-nginx

# Create application user
sudo useradd -m -s /bin/bash gitwiki
sudo usermod -aG sudo gitwiki
```

### Step 2: PostgreSQL Setup

```bash
# Switch to postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE gitwiki;
CREATE USER gitwiki WITH PASSWORD 'strong_password_here';
ALTER ROLE gitwiki SET client_encoding TO 'utf8';
ALTER ROLE gitwiki SET default_transaction_isolation TO 'read committed';
ALTER ROLE gitwiki SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE gitwiki TO gitwiki;

-- Exit
\q
```

**Configure PostgreSQL for remote access (if needed):**

Edit `/etc/postgresql/14/main/postgresql.conf`:
```conf
listen_addresses = 'localhost'  # Keep as localhost for security
```

Edit `/etc/postgresql/14/main/pg_hba.conf`:
```conf
# Add this line
local   gitwiki    gitwiki    md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Step 3: Redis Setup

```bash
# Configure Redis
sudo nano /etc/redis/redis.conf

# Set these values:
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

### Step 4: Application Setup

```bash
# Switch to gitwiki user
sudo su - gitwiki

# Create directory structure
mkdir -p /home/gitwiki/{app,logs,wiki_repo,wiki_static}
cd /home/gitwiki/app

# Clone repository
git clone https://github.com/your-org/gitwiki.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip wheel
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Create .env file
cp .env.example .env
nano .env
```

**Configure .env file:**

```bash
# Security
SECRET_KEY=<generate-with-command-below>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://gitwiki:strong_password_here@localhost:5432/gitwiki

# Redis
REDIS_URL=redis://localhost:6379/0

# Paths
WIKI_REPO_PATH=/home/gitwiki/wiki_repo
WIKI_STATIC_PATH=/home/gitwiki/wiki_static

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/gitwiki/logs/gitwiki.log

# Production settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True

# Email (configure your SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=email_password
```

**Generate SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 5: Django Setup

```bash
# Still as gitwiki user, with venv activated

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Install Git hooks
./scripts/install-hooks.sh

# Test configuration
python manage.py check --deploy
```

### Step 6: Gunicorn Setup

Create `/home/gitwiki/app/gunicorn_config.py`:

```python
import multiprocessing

# Gunicorn configuration file
bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 5

# Logging
accesslog = "/home/gitwiki/logs/gunicorn-access.log"
errorlog = "/home/gitwiki/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "gitwiki"

# Server mechanics
daemon = False
pidfile = "/home/gitwiki/app/gunicorn.pid"
user = "gitwiki"
group = "gitwiki"
```

Create systemd service `/etc/systemd/system/gitwiki.service`:

```ini
[Unit]
Description=GitWiki Gunicorn Application
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=gitwiki
Group=gitwiki
WorkingDirectory=/home/gitwiki/app
Environment="PATH=/home/gitwiki/app/venv/bin"
EnvironmentFile=/home/gitwiki/app/.env
ExecStart=/home/gitwiki/app/venv/bin/gunicorn \
    --config /home/gitwiki/app/gunicorn_config.py \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Step 7: Celery Setup

Create systemd service `/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=GitWiki Celery Worker
After=network.target redis-server.service

[Service]
Type=forking
User=gitwiki
Group=gitwiki
WorkingDirectory=/home/gitwiki/app
Environment="PATH=/home/gitwiki/app/venv/bin"
EnvironmentFile=/home/gitwiki/app/.env
ExecStart=/home/gitwiki/app/venv/bin/celery -A config worker \
    --loglevel=info \
    --logfile=/home/gitwiki/logs/celery-worker.log \
    --pidfile=/home/gitwiki/app/celery-worker.pid \
    --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Create systemd service `/etc/systemd/system/celery-beat.service`:

```ini
[Unit]
Description=GitWiki Celery Beat
After=network.target redis-server.service

[Service]
Type=forking
User=gitwiki
Group=gitwiki
WorkingDirectory=/home/gitwiki/app
Environment="PATH=/home/gitwiki/app/venv/bin"
EnvironmentFile=/home/gitwiki/app/.env
ExecStart=/home/gitwiki/app/venv/bin/celery -A config beat \
    --loglevel=info \
    --logfile=/home/gitwiki/logs/celery-beat.log \
    --pidfile=/home/gitwiki/app/celery-beat.pid \
    --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Enable and start services:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
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

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn psycopg2-binary

# Copy project
COPY . /app/

# Create directories
RUN mkdir -p /app/logs /app/wiki_repo /app/wiki_static

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
```

### docker-compose.yml

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=gitwiki
      - POSTGRES_USER=gitwiki
      - POSTGRES_PASSWORD=changeme
    restart: always

  redis:
    image: redis:7-alpine
    restart: always

  web:
    build: .
    command: gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application
    volumes:
      - ./wiki_repo:/app/wiki_repo
      - ./wiki_static:/app/wiki_static
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
    restart: always

  celery-worker:
    build: .
    command: celery -A config worker --loglevel=info
    volumes:
      - ./wiki_repo:/app/wiki_repo
      - ./logs:/app/logs
    env_file:
      - .env
    depends_on:
      - db
      - redis
    restart: always

  celery-beat:
    build: .
    command: celery -A config beat --loglevel=info
    volumes:
      - ./logs:/app/logs
    env_file:
      - .env
    depends_on:
      - db
      - redis
    restart: always

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./wiki_static:/app/wiki_static:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web
    restart: always

volumes:
  postgres_data:
```

### Deploy with Docker

```bash
# Create .env file
cp .env.example .env
# Edit .env with production values

# Build and start
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Check logs
docker-compose logs -f web
```

---

## Web Server Configuration

### Nginx Configuration

Create `/etc/nginx/sites-available/gitwiki`:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

# Upstream Gunicorn
upstream gitwiki_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect everything else to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logs
    access_log /var/log/nginx/gitwiki-access.log;
    error_log /var/log/nginx/gitwiki-error.log;

    # Max upload size (for images)
    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias /home/gitwiki/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Wiki static files (rendered HTML)
    location /wiki_static/ {
        alias /home/gitwiki/wiki_static/;
        expires 10m;
        add_header Cache-Control "public";
    }

    # Rate limit API endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://gitwiki_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Rate limit login
    location /admin/login/ {
        limit_req zone=login_limit burst=3 nodelay;
        proxy_pass http://gitwiki_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # All other requests
    location / {
        proxy_pass http://gitwiki_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Timeouts
        proxy_connect_timeout 75s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

**Enable site:**

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/gitwiki /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

## SSL/HTTPS Configuration

### Let's Encrypt (Certbot)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test renewal
sudo certbot renew --dry-run

# Auto-renewal is set up automatically via systemd timer
```

### Certificate Renewal

Certificates renew automatically, but verify:

```bash
# Check renewal timer
sudo systemctl status certbot.timer

# Manual renewal test
sudo certbot renew --dry-run
```

---

## Monitoring and Logging

### Log Aggregation

**View logs:**

```bash
# Application logs
tail -f /home/gitwiki/logs/gitwiki.log

# Gunicorn logs
tail -f /home/gitwiki/logs/gunicorn-access.log
tail -f /home/gitwiki/logs/gunicorn-error.log

# Celery logs
tail -f /home/gitwiki/logs/celery-worker.log
tail -f /home/gitwiki/logs/celery-beat.log

# Nginx logs
sudo tail -f /var/log/nginx/gitwiki-access.log
sudo tail -f /var/log/nginx/gitwiki-error.log
```

### System Monitoring

**Install monitoring tools:**

```bash
# htop for process monitoring
sudo apt install htop

# netdata for real-time monitoring
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
# Access at http://your-server-ip:19999
```

### Application Monitoring

**Sentry Setup:**

1. Create account at sentry.io
2. Create new project
3. Add to `.env`:
   ```bash
   SENTRY_DSN=https://your-dsn@sentry.io/project
   ```
4. Restart services:
   ```bash
   sudo systemctl restart gitwiki celery-worker
   ```

---

## Post-Deployment

### Verification Checklist

- [ ] Website loads at https://yourdomain.com
- [ ] SSL certificate is valid
- [ ] Login to /admin/ works
- [ ] Create test page works
- [ ] Edit and publish works
- [ ] Search works
- [ ] Images upload works
- [ ] All services running (gunicorn, celery, nginx)
- [ ] Logs show no errors
- [ ] Backup system configured

### Performance Testing

```bash
# Test with Apache Bench
ab -n 1000 -c 10 https://yourdomain.com/

# Test with wrk
wrk -t4 -c100 -d30s https://yourdomain.com/

# Target metrics:
# - Average response time < 200ms
# - 99th percentile < 500ms
# - No errors under load
```

### Initial Content

```bash
# As gitwiki user
cd /home/gitwiki/wiki_repo

# Create initial pages
echo "# Welcome to GitWiki" > README.md
mkdir -p docs
echo "# Documentation" > docs/README.md

# Commit
git add .
git commit -m "Initial content"

# Regenerate static files
python /home/gitwiki/app/manage.py full_static_rebuild
```

---

## Troubleshooting Deployment Issues

### Service Won't Start

```bash
# Check service status
sudo systemctl status gitwiki

# Check logs for errors
sudo journalctl -u gitwiki -n 50 --no-pager

# Check Gunicorn config
/home/gitwiki/app/venv/bin/gunicorn --check-config -c /home/gitwiki/app/gunicorn_config.py
```

### Database Connection Errors

```bash
# Test database connection
sudo -u gitwiki psql -h localhost -U gitwiki -d gitwiki

# Check PostgreSQL is running
sudo systemctl status postgresql

# Check DATABASE_URL in .env
grep DATABASE_URL /home/gitwiki/app/.env
```

### Static Files Not Loading

```bash
# Collect static files again
cd /home/gitwiki/app
source venv/bin/activate
python manage.py collectstatic --noinput

# Check file permissions
ls -la /home/gitwiki/app/staticfiles/

# Check Nginx configuration
sudo nginx -t
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew --force-renewal

# Check Nginx SSL configuration
sudo nginx -t
```

---

*For ongoing maintenance, see [Admin Guide](ADMIN_GUIDE.md). For development information, see [Developer Guide](../developer/DEVELOPER_GUIDE.md).*
