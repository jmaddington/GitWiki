"""
Tests for Editor Service.

AIDEV-NOTE: editor-tests; Comprehensive tests for all editor operations
"""

import os
import tempfile
import shutil
from pathlib import Path
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework import status

from .models import EditSession
from git_service.git_operations import GitRepository
from git_service.models import Configuration


class EditorAPITestCase(TestCase):
    """Test cases for Editor API endpoints."""

    def setUp(self):
        """Set up test environment."""
        # Import settings and git_operations to override
        from django.conf import settings
        from git_service import git_operations

        # Create temporary directory for test repository
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir) / 'test_repo'

        # Override the WIKI_REPO_PATH setting for tests
        self._original_repo_path = settings.WIKI_REPO_PATH
        settings.WIKI_REPO_PATH = self.repo_path

        # Reset the repository singleton
        git_operations._repo_instance = None

        # Create test repository
        self.repo = GitRepository(self.repo_path)

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Set up configuration
        Configuration.set_config('max_image_size_mb', '10')
        Configuration.set_config(
            'supported_image_formats',
            '["image/png", "image/jpeg", "image/webp"]'
        )

        self.client = Client()

    def tearDown(self):
        """Clean up test environment."""
        from django.conf import settings
        from git_service import git_operations

        # Reset repository singleton
        git_operations._repo_instance = None

        # Restore original repo path
        settings.WIKI_REPO_PATH = self._original_repo_path

        # Clean up test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_start_edit_new_file(self):
        """Test starting an edit session for a new file."""
        response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/test.md'
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('session_id', data)
        self.assertIn('branch_name', data)
        self.assertEqual(data['file_path'], 'docs/test.md')
        self.assertEqual(data['content'], '')  # New file
        self.assertTrue(data['markdown_valid'])

        # Verify session was created
        session = EditSession.objects.get(id=data['session_id'])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.file_path, 'docs/test.md')
        self.assertTrue(session.is_active)

    def test_start_edit_existing_file(self):
        """Test starting an edit session for an existing file."""
        # Create file in main branch first
        test_content = "# Test\nExisting content"
        self.repo.commit_changes(
            branch_name='main',
            file_path='docs/existing.md',
            content=test_content,
            commit_message='Create test file',
            user_info={'name': 'Test', 'email': 'test@example.com'}
        )

        response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/existing.md'
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['content'], test_content)

    def test_start_edit_resume_session(self):
        """Test resuming an existing edit session."""
        # Start first session
        response1 = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/test.md'
        }, content_type='application/json')

        session_id_1 = response1.json()['session_id']

        # Start second session for same file
        response2 = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/test.md'
        }, content_type='application/json')

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        data2 = response2.json()

        # Should return same session
        self.assertEqual(data2['session_id'], session_id_1)
        self.assertTrue(data2['resumed'])

    def test_start_edit_invalid_file_path(self):
        """Test starting edit with invalid file path."""
        response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': '../etc/passwd'  # Path traversal attempt
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/test.txt'  # Not a markdown file
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_validate_markdown_valid(self):
        """Test validating valid markdown."""
        response = self.client.post('/api/editor/validate/', {
            'content': '# Title\n\nParagraph with **bold** text.'
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['valid'])
        self.assertEqual(len(data['errors']), 0)

    def test_validate_markdown_warnings(self):
        """Test validating markdown with warnings."""
        response = self.client.post('/api/editor/validate/', {
            'content': '# Title\n\n```python\nunclosed code block'
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should have warnings about unclosed code block
        self.assertGreater(len(data['warnings']), 0)

    def test_commit_draft(self):
        """Test committing draft changes."""
        # Start edit session
        start_response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/test.md'
        }, content_type='application/json')

        session_id = start_response.json()['session_id']

        # Commit changes
        response = self.client.post('/api/editor/commit/', {
            'session_id': session_id,
            'content': '# Test\n\nCommitted content',
            'commit_message': 'Test commit'
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('commit_hash', data)
        self.assertIn('branch_name', data)

    def test_commit_draft_invalid_session(self):
        """Test committing with invalid session ID."""
        response = self.client.post('/api/editor/commit/', {
            'session_id': 99999,  # Non-existent session
            'content': '# Test',
            'commit_message': 'Test'
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_publish_edit_success(self):
        """Test publishing draft to main branch."""
        # Start edit session
        start_response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/test.md'
        }, content_type='application/json')

        session_id = start_response.json()['session_id']

        # Commit changes
        self.client.post('/api/editor/commit/', {
            'session_id': session_id,
            'content': '# Test\n\nPublished content',
            'commit_message': 'Test commit'
        }, content_type='application/json')

        # Publish
        response = self.client.post('/api/editor/publish/', {
            'session_id': session_id,
            'auto_push': False  # Don't push to remote in tests
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertTrue(data['published'])
        self.assertIn('url', data)

        # Verify session is now inactive
        session = EditSession.objects.get(id=session_id)
        self.assertFalse(session.is_active)

    def test_publish_edit_conflict(self):
        """Test publishing with merge conflict."""
        # Create file in main
        self.repo.commit_changes(
            branch_name='main',
            file_path='docs/conflict.md',
            content='# Original',
            commit_message='Create file',
            user_info={'name': 'Test', 'email': 'test@example.com'}
        )

        # Start edit session
        start_response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/conflict.md'
        }, content_type='application/json')

        session_id = start_response.json()['session_id']
        branch_name = start_response.json()['branch_name']

        # Commit changes to draft
        self.client.post('/api/editor/commit/', {
            'session_id': session_id,
            'content': '# Draft Version',
            'commit_message': 'Draft update'
        }, content_type='application/json')

        # Make conflicting change to main
        self.repo.commit_changes(
            branch_name='main',
            file_path='docs/conflict.md',
            content='# Main Version',
            commit_message='Main update',
            user_info={'name': 'Test', 'email': 'test@example.com'}
        )

        # Try to publish
        response = self.client.post('/api/editor/publish/', {
            'session_id': session_id,
            'auto_push': False
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertTrue(data['conflict'])
        self.assertIn('conflict_details', data)

        # Session should still be active
        session = EditSession.objects.get(id=session_id)
        self.assertTrue(session.is_active)

    def test_discard_draft(self):
        """Test discarding a draft."""
        # Start edit session
        start_response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'docs/test.md'
        }, content_type='application/json')

        session_id = start_response.json()['session_id']

        # Discard
        response = self.client.post('/api/editor/discard/', {
            'session_id': session_id
        }, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])

        # Session should be inactive
        session = EditSession.objects.get(id=session_id)
        self.assertFalse(session.is_active)


class EditSessionModelTestCase(TestCase):
    """Test cases for EditSession model."""

    def setUp(self):
        """Set up test environment."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

    def test_create_session(self):
        """Test creating an edit session."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='docs/test.md',
            branch_name='draft-1-abc123',
            is_active=True
        )

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.file_path, 'docs/test.md')
        self.assertTrue(session.is_active)

    def test_mark_inactive(self):
        """Test marking session as inactive."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='docs/test.md',
            branch_name='draft-1-abc123',
            is_active=True
        )

        session.mark_inactive()

        self.assertFalse(session.is_active)

    def test_get_active_sessions(self):
        """Test getting active sessions."""
        # Create active session
        EditSession.objects.create(
            user=self.user,
            file_path='docs/test1.md',
            branch_name='draft-1-abc123',
            is_active=True
        )

        # Create inactive session
        EditSession.objects.create(
            user=self.user,
            file_path='docs/test2.md',
            branch_name='draft-1-def456',
            is_active=False
        )

        active_sessions = EditSession.get_active_sessions(user=self.user)

        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions[0].file_path, 'docs/test1.md')

    def test_get_user_session_for_file(self):
        """Test getting session for specific user and file."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='docs/test.md',
            branch_name='draft-1-abc123',
            is_active=True
        )

        found_session = EditSession.get_user_session_for_file(
            self.user,
            'docs/test.md'
        )

        self.assertEqual(found_session.id, session.id)

        # Test with non-existent file
        no_session = EditSession.get_user_session_for_file(
            self.user,
            'docs/nonexistent.md'
        )

        self.assertIsNone(no_session)
