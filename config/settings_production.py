"""
Production settings for GitWiki.

This file contains production-specific settings including:
- Security headers
- HTTPS enforcement
- Database configuration
- Static file serving
- Logging configuration

To use these settings:
    export DJANGO_SETTINGS_MODULE=config.settings_production
    python manage.py runserver

Or in your WSGI application (e.g., Gunicorn):
    gunicorn config.wsgi:application --env DJANGO_SETTINGS_MODULE=config.settings_production
"""

# Import all settings from base settings.py
from .settings import *
import logging

logger = logging.getLogger(__name__)

# AIDEV-NOTE: production-config; Production-specific security and performance settings

# Override DEBUG for production
DEBUG = False
logger.info('Production settings loaded with DEBUG=False [SECURITY-04]')

# Security Headers - HTTPS enforcement
# IMPORTANT: Only enable these if you have HTTPS configured with SSL/TLS certificates

SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)

# Additional security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTP Strict Transport Security (HSTS)
# Only enable after confirming HTTPS works correctly
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)

if SECURE_SSL_REDIRECT:
    logger.info('HTTPS redirect enabled [SECURITY-05]')
if SECURE_HSTS_SECONDS > 0:
    logger.info(f'HSTS enabled for {SECURE_HSTS_SECONDS} seconds [SECURITY-06]')

# Database Configuration
# For production, use PostgreSQL instead of SQLite
# DATABASE_URL format: postgresql://user:password@host:port/dbname
if config('DATABASE_URL', default='').startswith('postgresql'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(config('DATABASE_URL'))
    }
    logger.info('Using PostgreSQL database [SECURITY-07]')
else:
    # Fall back to SQLite (not recommended for production)
    logger.warning('Using SQLite database - PostgreSQL recommended for production [SECURITY-08]')

# Static Files (collectstatic)
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Media Files
MEDIA_ROOT = BASE_DIR / 'media'

# Logging Configuration
# AIDEV-NOTE: production-logging; Centralized logging for production debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('LOG_FILE', default=str(BASE_DIR / 'logs' / 'gitwiki.log')),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('ERROR_LOG_FILE', default=str(BASE_DIR / 'logs' / 'gitwiki_errors.log')),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'git_service': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'editor': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'display': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
logs_dir = BASE_DIR / 'logs'
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f'Created logs directory at {logs_dir} [SECURITY-09]')

# Email Configuration (for error reporting)
if config('EMAIL_HOST', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@gitwiki.com')
    SERVER_EMAIL = config('SERVER_EMAIL', default='errors@gitwiki.com')
    ADMINS = [('Admin', config('ADMIN_EMAIL', default='admin@gitwiki.com'))]
    logger.info('Email configuration loaded [SECURITY-10]')
else:
    # Default to console email backend for testing
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    logger.warning('Email not configured - using console backend [SECURITY-11]')

# Sentry Error Tracking (optional)
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment=config('ENVIRONMENT', default='production'),
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
        # Adjust this value in production.
        traces_sample_rate=config('SENTRY_TRACES_SAMPLE_RATE', default=0.1, cast=float),
        # Send PII (personally identifiable information) to Sentry
        send_default_pii=False,
    )
    logger.info('Sentry error tracking enabled [SECURITY-12]')

# Cache Configuration (use Redis in production)
if config('REDIS_URL', default=''):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'gitwiki',
            'TIMEOUT': 300,  # 5 minutes default
        }
    }
    logger.info('Redis cache configured [SECURITY-13]')

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF Configuration
CSRF_COOKIE_HTTPONLY = False  # Required for AJAX requests
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Allowed hosts from environment
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

if not ALLOWED_HOSTS:
    logger.error('ALLOWED_HOSTS not configured - server will not accept any requests [SECURITY-14]')
else:
    logger.info(f'ALLOWED_HOSTS configured: {", ".join(ALLOWED_HOSTS)} [SECURITY-15]')

# Performance Settings
# Enable template caching
if not DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

# Celery Configuration (use Redis in production)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')

logger.info('Production settings loaded successfully [SECURITY-16]')
