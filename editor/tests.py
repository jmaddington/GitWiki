"""
Comprehensive tests for Editor Service.

AIDEV-NOTE: editor-tests; Tests for editing workflow, sessions, API endpoints, and conflict resolution
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.conf import settings
from pathlib import Path
import shutil
import tempfile
import json
import git

from .models import EditSession
from git_service.git_operations import GitRepository


class EditSessionModelTest(TestCase):
    """Tests for EditSession model."""

    def setUp(self):
        """Set up test user and session."""
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def test_create_session(self):
        """Test creating an edit session."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.file_path, 'test.md')
        self.assertTrue(session.is_active)

    def test_session_str(self):
        """Test string representation of session."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        str_repr = str(session)
        self.assertIn('Active', str_repr)
        self.assertIn('testuser', str_repr)
        self.assertIn('test.md', str_repr)

    def test_mark_inactive(self):
        """Test marking a session as inactive."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        session.mark_inactive()
        session.refresh_from_db()

        self.assertFalse(session.is_active)

    def test_touch(self):
        """Test updating last_modified timestamp."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        old_modified = session.last_modified
        session.touch()
        session.refresh_from_db()

        self.assertGreater(session.last_modified, old_modified)

    def test_get_active_sessions(self):
        """Test getting active sessions."""
        # Create active session
        active_session = EditSession.objects.create(
            user=self.user,
            file_path='active.md',
            branch_name='draft-1-test',
            is_active=True
        )

        # Create inactive session
        inactive_session = EditSession.objects.create(
            user=self.user,
            file_path='inactive.md',
            branch_name='draft-2-test',
            is_active=False
        )

        active_sessions = EditSession.get_active_sessions()

        self.assertIn(active_session, active_sessions)
        self.assertNotIn(inactive_session, active_sessions)

    def test_get_active_sessions_by_user(self):
        """Test getting active sessions filtered by user."""
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password')

        session1 = EditSession.objects.create(
            user=self.user,
            file_path='file1.md',
            branch_name='draft-1-test',
            is_active=True
        )

        session2 = EditSession.objects.create(
            user=user2,
            file_path='file2.md',
            branch_name='draft-2-test',
            is_active=True
        )

        user1_sessions = EditSession.get_active_sessions(user=self.user)

        self.assertIn(session1, user1_sessions)
        self.assertNotIn(session2, user1_sessions)

    def test_get_user_session_for_file(self):
        """Test getting session for specific user and file."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        found_session = EditSession.get_user_session_for_file(self.user, 'test.md')

        self.assertEqual(found_session, session)

    def test_get_user_session_for_file_not_found(self):
        """Test getting session that doesn't exist returns None."""
        found_session = EditSession.get_user_session_for_file(self.user, 'nonexistent.md')

        self.assertIsNone(found_session)


class EditorAPITest(TestCase):
    """Tests for Editor API endpoints."""

    def setUp(self):
        """Set up test environment with repository."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

        # Create temporary repository
        self.temp_repo_dir = Path(tempfile.mkdtemp())
        self.old_repo_path = settings.WIKI_REPO_PATH
        settings.WIKI_REPO_PATH = self.temp_repo_dir

        self.repo = GitRepository(repo_path=self.temp_repo_dir)

        # Create initial content
        self.repo.commit_changes(
            branch_name='main',
            file_path='existing.md',
            content='# Existing Page\nContent',
            commit_message='Initial commit',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

    def tearDown(self):
        """Clean up temporary directory."""
        if self.temp_repo_dir.exists():
            shutil.rmtree(self.temp_repo_dir)

        settings.WIKI_REPO_PATH = self.old_repo_path

    def test_start_edit_new_session(self):
        """Test starting a new edit session."""
        response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'test.md'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 201)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('branch_name', data['data'])
        self.assertIn('draft-', data['data']['branch_name'])

    def test_start_edit_resume_session(self):
        """Test resuming an existing session."""
        # Create a session first
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        # Start edit again - should resume
        response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id,
            'file_path': 'test.md'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['branch_name'], 'draft-1-test')
        self.assertTrue(data['data']['resumed'])

    def test_start_edit_validation_error(self):
        """Test start edit with invalid data."""
        response = self.client.post('/api/editor/start/', {
            'user_id': self.user.id
            # Missing file_path
        }, content_type='application/json')

        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data['success'])

    def test_save_draft(self):
        """Test saving draft content."""
        # Start a session first
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        # Create the branch
        self.repo.create_draft_branch(user_id=self.user.id, user=self.user)

        # Save draft
        response = self.client.post('/api/editor/save-draft/', {
            'session_id': session.id,
            'content': '# Test Content\nDraft text'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])

    def test_commit_draft(self):
        """Test committing draft to branch."""
        # Create branch and session
        branch_result = self.repo.create_draft_branch(user_id=self.user.id, user=self.user)
        branch_name = branch_result['branch_name']

        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name=branch_name,
            is_active=True
        )

        # Commit draft
        response = self.client.post('/api/editor/commit/', {
            'session_id': session.id,
            'content': '# Committed Content',
            'commit_message': 'Test commit',
            'user_info': {
                'name': 'Test User',
                'email': 'test@example.com'
            }
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('commit_hash', data['data'])

    def test_publish_edit(self):
        """Test publishing edit to main branch."""
        # Create branch with content
        branch_result = self.repo.create_draft_branch(user_id=self.user.id, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='new.md',
            content='# New Page',
            commit_message='Add new page',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        session = EditSession.objects.create(
            user=self.user,
            file_path='new.md',
            branch_name=branch_name,
            is_active=True
        )

        # Publish
        response = self.client.post('/api/editor/publish/', {
            'session_id': session.id
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertTrue(data['data']['merged'])

        # Session should be marked inactive
        session.refresh_from_db()
        self.assertFalse(session.is_active)

    def test_validate_markdown(self):
        """Test markdown validation endpoint."""
        response = self.client.post('/api/editor/validate/', {
            'content': '# Valid Markdown\nWith content'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertTrue(data['data']['is_valid'])

    def test_conflicts_list(self):
        """Test listing conflicts."""
        response = self.client.get('/api/editor/conflicts/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('conflicts', data['data'])

    def test_conflict_versions(self):
        """Test getting conflict versions for diff."""
        # Setup: Create a conflict scenario
        # Commit to main
        self.repo.commit_changes(
            branch_name='main',
            file_path='conflict.md',
            content='# Original',
            commit_message='Initial',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        # Create draft and modify
        branch_result = self.repo.create_draft_branch(user_id=self.user.id, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='conflict.md',
            content='# Modified in branch',
            commit_message='Branch edit',
            user_info={'name': 'User', 'email': 'user@example.com'},
            user=self.user
        )

        # Modify on main (creating conflict)
        self.repo.commit_changes(
            branch_name='main',
            file_path='conflict.md',
            content='# Modified in main',
            commit_message='Main edit',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        session = EditSession.objects.create(
            user=self.user,
            file_path='conflict.md',
            branch_name=branch_name,
            is_active=True
        )

        # Get versions
        response = self.client.get(f'/api/editor/conflict-versions/{session.id}/conflict.md/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('base', data['data'])
        self.assertIn('theirs', data['data'])
        self.assertIn('ours', data['data'])

    def test_resolve_conflict(self):
        """Test resolving a conflict."""
        # Setup conflict scenario
        self.repo.commit_changes(
            branch_name='main',
            file_path='resolve.md',
            content='# Original',
            commit_message='Initial',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        branch_result = self.repo.create_draft_branch(user_id=self.user.id, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='resolve.md',
            content='# Branch version',
            commit_message='Branch edit',
            user_info={'name': 'User', 'email': 'user@example.com'},
            user=self.user
        )

        self.repo.commit_changes(
            branch_name='main',
            file_path='resolve.md',
            content='# Main version',
            commit_message='Main edit',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        session = EditSession.objects.create(
            user=self.user,
            file_path='resolve.md',
            branch_name=branch_name,
            is_active=True
        )

        # Resolve
        response = self.client.post('/api/editor/resolve-conflict/', {
            'session_id': session.id,
            'file_path': 'resolve.md',
            'resolution_content': '# Resolved version',
            'user_info': {
                'name': 'User',
                'email': 'user@example.com'
            }
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])

    def test_binary_file_read(self):
        """Test reading binary files without corruption."""
        # Create a small test PNG (1x1 red pixel)
        test_png = (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x18\xdd\x8d\xb4'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        # Write binary file to repo
        image_path = 'images/test.png'
        file_full_path = self.repo.repo_path / image_path
        file_full_path.parent.mkdir(parents=True, exist_ok=True)
        file_full_path.write_bytes(test_png)

        self.repo.repo.index.add([image_path])
        self.repo.repo.index.commit(
            'Add test image',
            author=git.Actor('Test', 'test@example.com')
        )

        # Test that get_file_content_binary returns bytes without corruption
        binary_content = self.repo.get_file_content_binary(image_path, branch='main')

        # Verify content is bytes and matches original
        self.assertIsInstance(binary_content, bytes)
        self.assertEqual(binary_content, test_png, "Binary content should match original without corruption")
        self.assertEqual(len(binary_content), len(test_png))


class EditorViewsTest(TestCase):
    """Tests for editor UI views."""

    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def test_edit_page_view(self):
        """Test edit page renders."""
        response = self.client.get('/editor/edit/test.md')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test.md')

    def test_list_sessions_view(self):
        """Test sessions list view."""
        # Create a session
        EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        response = self.client.get('/editor/sessions/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test.md')

    def test_discard_session_view(self):
        """Test discarding a session."""
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        response = self.client.post(f'/editor/sessions/{session.id}/discard/')

        self.assertEqual(response.status_code, 302)  # Redirect

        # Session should be inactive
        session.refresh_from_db()
        self.assertFalse(session.is_active)

    def test_conflicts_list_view(self):
        """Test conflicts list view."""
        response = self.client.get('/editor/conflicts/')

        self.assertEqual(response.status_code, 200)


class ImageUploadTest(TestCase):
    """Tests for image upload functionality."""

    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

        # Create temporary repository
        self.temp_repo_dir = Path(tempfile.mkdtemp())
        self.old_repo_path = settings.WIKI_REPO_PATH
        settings.WIKI_REPO_PATH = self.temp_repo_dir

        self.repo = GitRepository(repo_path=self.temp_repo_dir)

    def tearDown(self):
        """Clean up."""
        if self.temp_repo_dir.exists():
            shutil.rmtree(self.temp_repo_dir)

        settings.WIKI_REPO_PATH = self.old_repo_path

    def test_upload_image_validation(self):
        """Test image upload endpoint validation."""
        # Create session
        branch_result = self.repo.create_draft_branch(user_id=self.user.id, user=self.user)
        session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name=branch_result['branch_name'],
            is_active=True
        )

        # Test validation error (no file)
        response = self.client.post('/api/editor/upload-image/', {
            'session_id': session.id
        }, content_type='application/json')

        self.assertEqual(response.status_code, 422)

class PermissionTest(TestCase):
    """Tests for permission checking."""

    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user('user1', 'user1@example.com', 'password')
        self.user2 = User.objects.create_user('user2', 'user2@example.com', 'password')

    def test_user_cannot_discard_other_session(self):
        """Test that users can't discard sessions they don't own."""
        # Create session for user1
        session = EditSession.objects.create(
            user=self.user1,
            file_path='test.md',
            branch_name='draft-1-test',
            is_active=True
        )

        # Login as user2
        self.client.force_login(self.user2)

        # Try to discard user1's session
        response = self.client.post(f'/editor/sessions/{session.id}/discard/')

        # Should redirect (permission denied)
        self.assertEqual(response.status_code, 302)

        # Session should still be active
        session.refresh_from_db()
        self.assertTrue(session.is_active)
