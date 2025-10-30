"""
Pytest configuration for GitWiki.

This file ensures Django is properly configured before running tests.
"""
import os
import django
from django.conf import settings

# Configure Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def pytest_configure(config):
    """Configure Django before running tests."""
    if not settings.configured:
        django.setup()
