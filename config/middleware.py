"""
Permission middleware for GitWiki.

This middleware enforces permission levels across all views:
- open: No authentication required (public wiki)
- read_only_public: Public read, authenticated edit
- private: Authentication required for all access

AIDEV-NOTE: permission-enforcement; Checks permission_level on every request
"""

import logging
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

logger = logging.getLogger(__name__)


class PermissionMiddleware:
    """
    Middleware to enforce permission levels throughout the application.

    Permission Modes:
    - "open": Anyone can view and edit (fully public wiki)
    - "read_only_public": Anyone can view, login required to edit
    - "private": Login required for all access

    Exempted URLs:
    - /admin/ (Django admin always requires authentication)
    - /accounts/login/ (login page itself)
    - /accounts/logout/ (logout functionality)
    - /static/ and /media/ (static assets)
    """

    # URLs that are always accessible without authentication
    EXEMPT_PATHS = [
        '/admin/',
        '/accounts/login/',
        '/accounts/logout/',
        '/static/',
        '/media/',
    ]

    # URLs that require edit permissions
    EDIT_PATHS = [
        '/editor/',
        '/api/git/branch/',
        '/api/git/commit/',
        '/api/git/publish/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if path is exempt from permission checks
        if self._is_exempt_path(request.path):
            return self.get_response(request)

        # Get permission level from configuration
        permission_level = self._get_permission_level()

        # Apply permission checks based on mode
        if permission_level == 'private':
            # Private mode: authentication required for all access
            if not request.user.is_authenticated:
                logger.info(f'Private mode: blocking unauthenticated access to {request.path} [PERM-01]')
                messages.warning(request, 'This wiki is private. Please log in to access.')
                return redirect(f"{reverse('login')}?next={request.path}")

        elif permission_level == 'read_only_public':
            # Read-only public: authentication required for edit operations
            if self._is_edit_path(request.path):
                if not request.user.is_authenticated:
                    logger.info(f'Read-only mode: blocking unauthenticated edit to {request.path} [PERM-02]')
                    messages.warning(request, 'Login required to edit pages.')
                    return redirect(f"{reverse('login')}?next={request.path}")

        elif permission_level == 'open':
            # Open mode: no restrictions (fully public wiki)
            pass

        else:
            # Unknown permission level - default to private for security
            logger.warning(f'Unknown permission level: {permission_level}, defaulting to private [PERM-03]')
            if not request.user.is_authenticated:
                return redirect(f"{reverse('login')}?next={request.path}")

        # Permission check passed, proceed with request
        response = self.get_response(request)
        return response

    def _is_exempt_path(self, path):
        """Check if path is exempt from permission checks."""
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return True
        return False

    def _is_edit_path(self, path):
        """Check if path requires edit permissions."""
        for edit_path in self.EDIT_PATHS:
            if path.startswith(edit_path):
                return True
        return False

    def _get_permission_level(self):
        """
        Get permission level from Configuration model.

        Returns default 'read_only_public' if not configured.
        """
        try:
            from git_service.models import Configuration
            config = Configuration.get_config('permission_level')

            # Validate permission level
            valid_levels = ['open', 'read_only_public', 'private']
            if config not in valid_levels:
                logger.warning(f'Invalid permission level in config: {config}, using default [PERM-04]')
                return 'read_only_public'

            return config
        except Exception as e:
            # If Configuration model is not available or database error,
            # default to read_only_public for security
            logger.error(f'Error getting permission level: {e}, using default [PERM-05]')
            return 'read_only_public'
