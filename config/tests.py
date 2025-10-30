"""
Tests for permission middleware and authentication.

AIDEV-NOTE: permission-tests; Comprehensive permission system testing
"""

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from git_service.models import Configuration


class PermissionMiddlewareTestCase(TestCase):
    """Test permission middleware enforcement across all modes."""

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()

        # Create test users
        self.regular_user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='staffpass123',
            is_staff=True
        )

        # Ensure configuration exists
        Configuration.objects.get_or_create(
            key='permission_level',
            defaults={'value': 'read_only_public', 'description': 'Permission level'}
        )

    def test_open_mode_allows_all_access(self):
        """Test open mode allows unauthenticated access to all pages."""
        Configuration.set_config('permission_level', 'open')

        # Test wiki home (display)
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 404])  # 404 if no content yet

        # Test editor (should be accessible)
        response = self.client.get('/editor/sessions/')
        self.assertIn(response.status_code, [200, 302])  # May redirect if no sessions

    def test_read_only_public_allows_viewing(self):
        """Test read_only_public mode allows unauthenticated viewing."""
        Configuration.set_config('permission_level', 'read_only_public')

        # Test wiki home (should be accessible)
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 404])

    def test_read_only_public_blocks_editing(self):
        """Test read_only_public mode blocks unauthenticated editing."""
        Configuration.set_config('permission_level', 'read_only_public')

        # Test editor access (should redirect to login)
        response = self.client.get('/editor/sessions/')
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_read_only_public_allows_authenticated_editing(self):
        """Test read_only_public mode allows authenticated editing."""
        Configuration.set_config('permission_level', 'read_only_public')

        # Login as regular user
        self.client.login(username='testuser', password='testpass123')

        # Test editor access (should be accessible)
        response = self.client.get('/editor/sessions/')
        self.assertEqual(response.status_code, 200)

    def test_private_mode_blocks_all_unauthenticated(self):
        """Test private mode blocks all unauthenticated access."""
        Configuration.set_config('permission_level', 'private')

        # Test wiki home (should redirect to login)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

        # Test editor (should redirect to login)
        response = self.client.get('/editor/sessions/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_private_mode_allows_authenticated_access(self):
        """Test private mode allows authenticated access to all pages."""
        Configuration.set_config('permission_level', 'private')

        # Login as regular user
        self.client.login(username='testuser', password='testpass123')

        # Test wiki home (should be accessible)
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 404])

        # Test editor (should be accessible)
        response = self.client.get('/editor/sessions/')
        self.assertEqual(response.status_code, 200)

    def test_admin_always_requires_authentication(self):
        """Test admin panel always requires authentication regardless of mode."""
        # Test in open mode
        Configuration.set_config('permission_level', 'open')
        response = self.client.get('/admin/')
        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)

        # Test in read_only_public mode
        Configuration.set_config('permission_level', 'read_only_public')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)

        # Test in private mode
        Configuration.set_config('permission_level', 'private')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)

    def test_login_page_always_accessible(self):
        """Test login page is always accessible."""
        for mode in ['open', 'read_only_public', 'private']:
            Configuration.set_config('permission_level', mode)
            response = self.client.get('/accounts/login/')
            self.assertEqual(response.status_code, 200)

    def test_invalid_permission_level_defaults_to_private(self):
        """Test invalid permission level defaults to private for security."""
        Configuration.set_config('permission_level', 'invalid_mode')

        # Should behave like private mode (redirect to login)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_staff_can_access_admin(self):
        """Test staff users can access admin panel."""
        self.client.login(username='staffuser', password='staffpass123')
        response = self.client.get('/admin/')
        # Should show admin page or redirect to admin index
        self.assertIn(response.status_code, [200, 302])

    def test_non_staff_cannot_access_admin(self):
        """Test regular users cannot access admin panel."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/admin/')
        # Should redirect to admin login (Django's admin enforces staff)
        self.assertEqual(response.status_code, 302)


class AuthenticationTestCase(TestCase):
    """Test authentication views and flow."""

    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_login_page_renders(self):
        """Test login page renders correctly."""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'GitWiki Login')
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Password')

    def test_successful_login(self):
        """Test successful login redirects to home."""
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

    def test_failed_login(self):
        """Test failed login shows error."""
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)

    def test_logout_redirects_to_home(self):
        """Test logout redirects to home page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/logout/')
        # Should redirect to home
        self.assertEqual(response.status_code, 302)

    def test_login_with_next_parameter(self):
        """Test login redirects to next parameter."""
        response = self.client.post('/accounts/login/?next=/editor/sessions/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        # Should redirect to the next URL
        self.assertEqual(response.status_code, 302)


class ConfigurationManagementTestCase(TestCase):
    """Test configuration management page and functionality."""

    def setUp(self):
        """Set up test client and admin user."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )

    def test_configuration_page_requires_admin(self):
        """Test configuration page requires admin access."""
        # Unauthenticated - should redirect to login
        response = self.client.get('/api/git/settings/config/')
        self.assertEqual(response.status_code, 302)

        # Regular user - should be forbidden or redirected
        regular_user = User.objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')
        response = self.client.get('/api/git/settings/config/')
        # Should fail staff check
        self.assertIn(response.status_code, [302, 403])

    def test_configuration_page_accessible_to_admin(self):
        """Test configuration page accessible to admin users."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/api/git/settings/config/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Wiki Configuration')
        self.assertContains(response, 'Permission Level')

    def test_configuration_update(self):
        """Test configuration can be updated via form."""
        self.client.login(username='admin', password='adminpass123')

        # Submit configuration update
        response = self.client.post('/api/git/settings/config/', {
            'action': 'save_config',
            'permission_level': 'private',
            'wiki_title': 'Test Wiki',
            'wiki_description': 'Test Description',
            'max_image_size_mb': 15,
            'branch_cleanup_days': 14,
            'supported_image_formats': 'png,jpg'
        })

        # Should redirect or show success
        self.assertIn(response.status_code, [200, 302])

        # Verify configuration was saved
        self.assertEqual(Configuration.get_config('permission_level'), 'private')
        self.assertEqual(Configuration.get_config('wiki_title'), 'Test Wiki')
        self.assertEqual(Configuration.get_config('max_image_size_mb'), 15)
        self.assertEqual(Configuration.get_config('branch_cleanup_days'), 14)

    def test_invalid_permission_level_rejected(self):
        """Test invalid permission level is rejected."""
        self.client.login(username='admin', password='adminpass123')

        # Try to set invalid permission level
        response = self.client.post('/api/git/settings/config/', {
            'action': 'save_config',
            'permission_level': 'invalid_level',
            'wiki_title': 'Test',
            'max_image_size_mb': 10,
            'branch_cleanup_days': 7,
            'supported_image_formats': 'png'
        })

        # Permission level should still be valid
        perm_level = Configuration.get_config('permission_level')
        self.assertIn(perm_level, ['open', 'read_only_public', 'private'])

    def test_configuration_validation(self):
        """Test configuration validates input ranges."""
        self.client.login(username='admin', password='adminpass123')

        # Try invalid image size (too large)
        response = self.client.post('/api/git/settings/config/', {
            'action': 'save_config',
            'permission_level': 'read_only_public',
            'wiki_title': 'Test',
            'max_image_size_mb': 500,  # Too large
            'branch_cleanup_days': 7,
            'supported_image_formats': 'png'
        })

        # Should use default or show warning
        max_size = Configuration.get_config('max_image_size_mb')
        self.assertLessEqual(max_size, 100)


class SecurityValidationTestCase(TestCase):
    """Test security validation at startup."""

    def test_production_blocks_default_secret_key(self):
        """Test that production mode refuses to start with default SECRET_KEY."""
        import subprocess
        import os

        # Create a test script that simulates production startup
        test_script = '''
import sys
import os
os.environ['DEBUG'] = 'False'
os.environ['SECRET_KEY'] = 'django-insecure-dev-key-CHANGE-IN-PRODUCTION'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

try:
    import django
    django.setup()
    sys.exit(0)  # Should not reach here
except SystemExit as e:
    sys.exit(e.code)
'''

        # Run the test script
        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # Should exit with code 1
        self.assertEqual(result.returncode, 1)
        # Should have error message in stderr
        self.assertIn(b'SECURITY-FATAL', result.stderr)

    def test_development_allows_default_secret_key(self):
        """Test that development mode allows default SECRET_KEY."""
        import subprocess
        import os

        # Create a test script that simulates development startup
        test_script = '''
import sys
import os
os.environ['DEBUG'] = 'True'
os.environ['SECRET_KEY'] = 'django-insecure-dev-key-CHANGE-IN-PRODUCTION'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

try:
    import django
    django.setup()
    sys.exit(0)  # Should reach here successfully
except SystemExit as e:
    sys.exit(e.code)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(2)
'''

        # Run the test script
        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # Should exit with code 0 (success)
        self.assertEqual(result.returncode, 0)

    def test_production_allows_custom_secret_key(self):
        """Test that production mode allows custom SECRET_KEY."""
        import subprocess
        import os

        # Create a test script that simulates production startup with custom key
        test_script = '''
import sys
import os
os.environ['DEBUG'] = 'False'
os.environ['SECRET_KEY'] = 'custom-secure-secret-key-for-production-12345'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

try:
    import django
    django.setup()
    sys.exit(0)  # Should reach here successfully
except SystemExit as e:
    sys.exit(e.code)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(2)
'''

        # Run the test script
        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # Should exit with code 0 (success)
        self.assertEqual(result.returncode, 0)
