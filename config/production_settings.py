"""
Production settings for GitWiki.

This file contains production-specific settings that override development settings.

IMPORTANT: Never commit secrets to version control. All sensitive values should
come from environment variables.

Usage:
    export DJANGO_SETTINGS_MODULE=config.production_settings
    python manage.py runserver

Environment Variables Required:
    - DJANGO_SECRET_KEY: Django secret key (50+ chars)
    - DATABASE_URL: PostgreSQL connection string
    - REDIS_URL: Redis connection string
    - ALLOWED_HOSTS: Comma-separated list of allowed hosts
"""

import os
from .settings import *

# AIDEV-NOTE: production-security - Security settings for production deployment

# ============================================================================
# CRITICAL SECURITY SETTINGS
# ============================================================================

# DEBUG must be False in production
DEBUG = False

# SECRET_KEY must come from environment
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError(
        "DJANGO_SECRET_KEY environment variable must be set. "
        "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(50))'"
    )

# ALLOWED_HOSTS must be explicitly set
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError(
        "ALLOWED_HOSTS environment variable must be set. "
        "Example: ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com"
    )

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Use PostgreSQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'gitwiki'),
        'USER': os.environ.get('DB_USER', 'gitwiki'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

if not os.environ.get('DB_PASSWORD'):
    raise ValueError("DB_PASSWORD environment variable must be set")

# ============================================================================
# HTTPS AND SECURITY HEADERS
# ============================================================================

# Force HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security headers
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Proxy header for HTTPS detection (if behind reverse proxy)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================================================
# SESSION SECURITY
# ============================================================================

# Session cookie settings
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24 hours

# CSRF cookie settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# STATIC AND MEDIA FILES
# ============================================================================

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files (user uploads)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'gitwiki.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'git_service': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'editor': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'display': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# ============================================================================
# EMAIL CONFIGURATION (for error notifications)
# ============================================================================

# Configure if you want email notifications for errors
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', '')),
]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'gitwiki@example.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Redis cache (production)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'gitwiki',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Cache timeouts for different operations
CACHE_TIMEOUT_SEARCH = 300  # 5 minutes
CACHE_TIMEOUT_CONFLICTS = 120  # 2 minutes
CACHE_TIMEOUT_PAGE_HISTORY = 600  # 10 minutes
CACHE_TIMEOUT_DIRECTORY_LISTING = 300  # 5 minutes
CACHE_TIMEOUT_CONFIG = 3600  # 1 hour

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

# Use Redis as broker in production
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

# Task time limits
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes

# ============================================================================
# ADDITIONAL SECURITY SETTINGS
# ============================================================================

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Stronger password requirement
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# File upload security
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================

# Template caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# Disable debug toolbar in production
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS.remove('debug_toolbar')

if 'debug_toolbar.middleware.DebugToolbarMiddleware' in MIDDLEWARE:
    MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')

# ============================================================================
# MONITORING AND HEALTH CHECKS
# ============================================================================

# Health check endpoint (add to urls.py)
# Allow health check without authentication
HEALTH_CHECK_URL = '/health/'

# ============================================================================
# BACKUP SETTINGS
# ============================================================================

# Git repository backup path
GIT_BACKUP_PATH = os.environ.get('GIT_BACKUP_PATH', '/var/backups/gitwiki/')

# Database backup retention (days)
DB_BACKUP_RETENTION_DAYS = int(os.environ.get('DB_BACKUP_RETENTION_DAYS', 30))

# ============================================================================
# NOTES FOR DEPLOYMENT
# ============================================================================

"""
Required Environment Variables:
    DJANGO_SECRET_KEY=<50+ character random string>
    DATABASE_URL=postgresql://user:pass@localhost/gitwiki
    REDIS_URL=redis://localhost:6379/0
    ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

Optional Environment Variables:
    DB_NAME=gitwiki
    DB_USER=gitwiki
    DB_PASSWORD=<secure password>
    DB_HOST=localhost
    DB_PORT=5432
    ADMIN_EMAIL=admin@example.com
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER=your-email@gmail.com
    EMAIL_HOST_PASSWORD=your-app-password
    DEFAULT_FROM_EMAIL=gitwiki@yourdomain.com
    GIT_BACKUP_PATH=/var/backups/gitwiki/
    DB_BACKUP_RETENTION_DAYS=30

Generate SECRET_KEY:
    python -c 'import secrets; print(secrets.token_urlsafe(50))'

Test production settings locally:
    export DJANGO_SETTINGS_MODULE=config.production_settings
    export DJANGO_SECRET_KEY=<your-key>
    export ALLOWED_HOSTS=localhost,127.0.0.1
    export DB_PASSWORD=<password>
    python manage.py check --deploy
"""
