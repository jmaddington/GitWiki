"""
Authentication tests for Git Service API endpoints.

Tests that all destructive git_service API endpoints require authentication.
"""

import json
import tempfile
import shutil
from pathlib import Path
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.conf import settings
from git_service.git_operations import GitRepository
from git_service import git_operations
from config.api_utils import get_user_info_for_commit


class GitServiceAuthenticationTest(TestCase):
    """Tests for authentication requirements on git service API endpoints."""

    def setUp(self):
        """Set up test environment with repository."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

        # Create temporary repository
        self.temp_repo_dir = Path(tempfile.mkdtemp())
        self.old_repo_path = settings.WIKI_REPO_PATH
        settings.WIKI_REPO_PATH = self.temp_repo_dir

        self.repo = GitRepository(repo_path=self.temp_repo_dir)

        # Set permission level to allow authenticated edits
        from git_service.models import Configuration
        Configuration.set_config('permission_level', 'open')

        # Create initial content
        self.repo.commit_changes(
            branch_name='main',
            file_path='test.md',
            content='# Test Page\nContent',
            commit_message='Initial commit',
            user_info=get_user_info_for_commit(self.user),
            user=self.user
        )

    def tearDown(self):
        """Clean up temporary directory."""
        if self.temp_repo_dir.exists():
            shutil.rmtree(self.temp_repo_dir)

        settings.WIKI_REPO_PATH = self.old_repo_path

        # Clear repository singleton to prevent state pollution between tests
        git_operations.reset_repository_singleton_for_testing()

    def test_unauthenticated_create_branch(self):
        """Test that unauthenticated users cannot create branches."""
        response = self.client.post('/api/git/branch/create/',
            content_type='application/json')

        # API returns 403 or redirects to login (302)
        self.assertIn(response.status_code, [302, 403])

    def test_authenticated_create_branch(self):
        """Test that authenticated users can create branches (not blocked by auth)."""
        self.client.force_login(self.user)

        response = self.client.post('/api/git/branch/create/',
            content_type='application/json')

        # Should not be 302 (redirect) or 403 (forbidden) - authentication passed
        self.assertNotIn(response.status_code, [302, 403])

    def test_unauthenticated_commit_changes(self):
        """Test that unauthenticated users cannot commit changes."""
        response = self.client.post('/api/git/commit/', {
            'branch_name': 'main',
            'file_path': 'test2.md',
            'content': '# Test 2',
            'commit_message': 'Test commit'
        }, content_type='application/json')

        # API returns 403 or redirects to login (302)
        self.assertIn(response.status_code, [302, 403])

    def test_authenticated_commit_changes(self):
        """Test that authenticated users can commit changes."""
        self.client.force_login(self.user)

        # Create a draft branch first
        branch_response = self.client.post('/api/git/branch/create/',
            content_type='application/json')

        if branch_response.status_code == 200:
            branch_data = branch_response.json()
            branch_name = branch_data['data']['branch_name']

            response = self.client.post('/api/git/commit/', {
                'branch_name': branch_name,
                'file_path': 'test2.md',
                'content': '# Test 2',
                'commit_message': 'Test commit'
            }, content_type='application/json')

            # Should not be blocked by authentication
            self.assertNotIn(response.status_code, [302, 403])

    def test_unauthenticated_publish_draft(self):
        """Test that unauthenticated users cannot publish drafts."""
        # Create a draft branch first as authenticated user
        self.client.force_login(self.user)
        branch_response = self.client.post('/api/git/branch/create/',
            content_type='application/json')

        if branch_response.status_code == 200:
            branch_data = branch_response.json()
            branch_name = branch_data['data']['branch_name']

            # Commit something to the branch
            self.client.post('/api/git/commit/', {
                'branch_name': branch_name,
                'file_path': 'test2.md',
                'content': '# Test 2',
                'commit_message': 'Test commit'
            }, content_type='application/json')

            # Logout and try to publish
            self.client.logout()

            response = self.client.post('/api/git/publish/', {
                'branch_name': branch_name,
                'auto_push': False
            }, content_type='application/json')

            # API returns 403 or redirects to login (302)
            self.assertIn(response.status_code, [302, 403])

    def test_authenticated_publish_draft(self):
        """Test that authenticated users can publish drafts."""
        self.client.force_login(self.user)

        # Create a draft branch
        branch_response = self.client.post('/api/git/branch/create/',
            content_type='application/json')

        if branch_response.status_code == 200:
            branch_data = branch_response.json()
            branch_name = branch_data['data']['branch_name']

            # Commit something to the branch
            self.client.post('/api/git/commit/', {
                'branch_name': branch_name,
                'file_path': 'test2.md',
                'content': '# Test 2',
                'commit_message': 'Test commit'
            }, content_type='application/json')

            # Publish
            response = self.client.post('/api/git/publish/', {
                'branch_name': branch_name,
                'auto_push': False
            }, content_type='application/json')

            # Should not be blocked by authentication
            self.assertNotIn(response.status_code, [302, 403])
