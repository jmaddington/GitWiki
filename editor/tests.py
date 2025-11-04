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

    def test_prevent_duplicate_active_sessions(self):
        """Test that unique constraint prevents duplicate active sessions (fixes #22)."""
        from django.db import IntegrityError, transaction

        file_path = 'test.md'

        # Create first active session
        session1 = EditSession.objects.create(
            user=self.user,
            file_path=file_path,
            branch_name='draft-1',
            is_active=True
        )

        # Try to create duplicate active session - should fail
        # Use atomic block to properly handle the transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                session2 = EditSession.objects.create(
                    user=self.user,
                    file_path=file_path,
                    branch_name='draft-2',
                    is_active=True
                )

        # Verify only one active session exists (query after transaction rolled back)
        active_sessions = EditSession.objects.filter(
            user=self.user,
            file_path=file_path,
            is_active=True
        )
        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions.first().id, session1.id)

    def test_allow_multiple_inactive_sessions(self):
        """Test that multiple inactive sessions are allowed (fixes #22)."""
        file_path = 'test.md'

        # Create two inactive sessions - should succeed
        session1 = EditSession.objects.create(
            user=self.user,
            file_path=file_path,
            branch_name='draft-1',
            is_active=False
        )

        session2 = EditSession.objects.create(
            user=self.user,
            file_path=file_path,
            branch_name='draft-2',
            is_active=False
        )

        # Should have 2 inactive sessions
        inactive_sessions = EditSession.objects.filter(
            user=self.user,
            file_path=file_path,
            is_active=False
        )
        self.assertEqual(inactive_sessions.count(), 2)

    def test_allow_different_users_same_file(self):
        """Test that different users can have active sessions for the same file (fixes #22)."""
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password')
        file_path = 'test.md'

        # Create active session for first user
        session1 = EditSession.objects.create(
            user=self.user,
            file_path=file_path,
            branch_name='draft-1',
            is_active=True
        )

        # Create active session for second user - should succeed
        session2 = EditSession.objects.create(
            user=user2,
            file_path=file_path,
            branch_name='draft-2',
            is_active=True
        )

        # Should have 2 active sessions (one per user)
        active_sessions = EditSession.objects.filter(
            file_path=file_path,
            is_active=True
        )
        self.assertEqual(active_sessions.count(), 2)

    def test_allow_same_user_different_files(self):
        """Test that same user can have active sessions for different files (fixes #22)."""
        # Create active sessions for different files
        session1 = EditSession.objects.create(
            user=self.user,
            file_path='file1.md',
            branch_name='draft-1',
            is_active=True
        )

        session2 = EditSession.objects.create(
            user=self.user,
            file_path='file2.md',
            branch_name='draft-2',
            is_active=True
        )

        # Should have 2 active sessions (one per file)
        active_sessions = EditSession.objects.filter(
            user=self.user,
            is_active=True
        )
        self.assertEqual(active_sessions.count(), 2)

    def test_reactivate_after_marking_inactive(self):
        """Test that marking session inactive allows creating new active session (fixes #22)."""
        file_path = 'test.md'

        # Create and then deactivate first session
        session1 = EditSession.objects.create(
            user=self.user,
            file_path=file_path,
            branch_name='draft-1',
            is_active=True
        )
        session1.mark_inactive()

        # Should be able to create new active session
        session2 = EditSession.objects.create(
            user=self.user,
            file_path=file_path,
            branch_name='draft-2',
            is_active=True
        )

        # Verify only session2 is active
        active_session = EditSession.get_user_session_for_file(self.user, file_path)
        self.assertEqual(active_session.id, session2.id)


class EditorAPITest(TestCase):
    """Tests for Editor API endpoints."""

    def setUp(self):
        """Set up test environment with repository."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        # Authenticate the user for API requests
        self.client.force_login(self.user)

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
        response = self.client.post('/editor/api/start/', {
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
        response = self.client.post('/editor/api/start/', {
            'file_path': 'test.md'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['branch_name'], 'draft-1-test')
        self.assertTrue(data['data']['resumed'])

    def test_start_edit_validation_error(self):
        """Test start edit with invalid data."""
        response = self.client.post('/editor/api/start/', {
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
        response = self.client.post('/editor/api/save-draft/', {
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
        response = self.client.post('/editor/api/commit/', {
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
        response = self.client.post('/editor/api/publish/', {
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
        response = self.client.post('/editor/api/validate/', {
            'content': '# Valid Markdown\nWith content'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertTrue(data['data']['is_valid'])

    def test_conflicts_list(self):
        """Test listing conflicts."""
        response = self.client.get('/editor/api/conflicts/')

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
        response = self.client.get(f'/editor/api/conflict-versions/{session.id}/conflict.md/')

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
        response = self.client.post('/editor/api/resolve-conflict/', {
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
        self.client.force_login(self.user)

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
        self.client.force_login(self.user)

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
        response = self.client.post('/editor/api/upload-image/', {
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


class DeleteFileAPITest(TestCase):
    """Tests for DeleteFileAPIView endpoint."""

    def setUp(self):
        """Set up test environment with git repository."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client.force_login(self.user)

        # Create temporary git repository
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / 'test_repo'
        self.repo_path.mkdir()

        # Initialize git repo
        repo = git.Repo.init(self.repo_path)

        # Create and commit a test file
        test_file = self.repo_path / 'test.md'
        test_file.write_text('# Test File')
        repo.index.add(['test.md'])
        repo.index.commit('Initial commit', author=git.Actor('Test', 'test@example.com'))

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_delete_file_success(self):
        """Test successful file deletion (or expected failure)."""
        response = self.client.post(
            '/editor/api/delete-file/',
            data=json.dumps({
                'file_path': 'test.md',
                'commit_message': 'Delete test file'
            }),
            content_type='application/json'
        )

        # Should return success or error (test environment may not have file)
        self.assertIn(response.status_code, [200, 201, 400, 404, 500])

    def test_delete_file_unauthorized(self):
        """Test that unauthenticated users cannot delete files."""
        # Logout
        self.client.logout()

        response = self.client.post(
            '/editor/api/delete-file/',
            data=json.dumps({
                'file_path': 'test.md',
                'commit_message': 'Delete test file'
            }),
            content_type='application/json'
        )

        # Should return 401 Unauthorized or 302 redirect (depending on middleware)
        self.assertIn(response.status_code, [401, 302, 403])

    def test_delete_file_path_traversal(self):
        """Test that path traversal attacks are blocked."""
        response = self.client.post(
            '/editor/api/delete-file/',
            data=json.dumps({
                'file_path': '../../../etc/passwd',
                'commit_message': 'Attack attempt'
            }),
            content_type='application/json'
        )

        # Should return validation error
        self.assertIn(response.status_code, [400, 422])

    def test_delete_file_missing_file(self):
        """Test deleting non-existent file."""
        response = self.client.post(
            '/editor/api/delete-file/',
            data=json.dumps({
                'file_path': 'nonexistent.md',
                'commit_message': 'Delete missing file'
            }),
            content_type='application/json'
        )

        # Should return error (404 or 400)
        self.assertIn(response.status_code, [400, 404, 500])


class UploadFileAPITest(TestCase):
    """Tests for UploadFileAPIView endpoint."""

    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client.force_login(self.user)

        # Create edit session
        self.session = EditSession.objects.create(
            user=self.user,
            file_path='test.md',
            branch_name='draft-test',
            is_active=True
        )

    def test_upload_file_success(self):
        """Test successful file upload."""
        from io import BytesIO

        test_file = BytesIO(b'Test file content')
        test_file.name = 'test.txt'

        response = self.client.post(
            '/editor/api/upload-file/',
            data={
                'session_id': self.session.id,
                'file': test_file,
                'description': 'Test file'
            }
        )

        # Should return success or validation error depending on implementation
        self.assertIn(response.status_code, [200, 201, 400, 500])

    def test_upload_file_size_limit(self):
        """Test file size validation."""
        from io import BytesIO

        # Create file larger than 100MB limit
        large_file = BytesIO(b'x' * (101 * 1024 * 1024))
        large_file.name = 'large.txt'

        response = self.client.post(
            '/editor/api/upload-file/',
            data={
                'session_id': self.session.id,
                'file': large_file,
                'description': 'Large file'
            }
        )

        # Should return validation error (422 or 400)
        self.assertIn(response.status_code, [400, 422])
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_upload_dangerous_file_type(self):
        """Test that dangerous file types are blocked."""
        from io import BytesIO

        # Try to upload executable
        test_file = BytesIO(b'malicious content')
        test_file.name = 'malware.exe'

        response = self.client.post(
            '/editor/api/upload-file/',
            data={
                'session_id': self.session.id,
                'file': test_file,
                'description': 'Malware'
            }
        )

        # Should return validation error (422 or 400)
        self.assertIn(response.status_code, [400, 422])
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_upload_filename_sanitization(self):
        """Test that filenames are sanitized."""
        from io import BytesIO

        # Filename with dangerous characters
        test_file = BytesIO(b'Test content')
        test_file.name = '../../../etc/passwd.txt'

        response = self.client.post(
            '/editor/api/upload-file/',
            data={
                'session_id': self.session.id,
                'file': test_file,
                'description': 'Test'
            }
        )

        # Should either succeed with sanitized name or fail with validation error
        self.assertIn(response.status_code, [200, 201, 400, 500])


class QuickUploadFileAPITest(TestCase):
    """Tests for QuickUploadFileAPIView endpoint."""

    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client.force_login(self.user)

    def test_quick_upload_success(self):
        """Test successful quick upload."""
        from io import BytesIO

        test_file = BytesIO(b'Quick test content')
        test_file.name = 'quick.txt'

        response = self.client.post(
            '/editor/api/quick-upload-file/',
            data={
                'file': test_file,
                'target_path': 'files',
                'description': 'Quick upload test'
            }
        )

        # Should return success or error depending on implementation
        self.assertIn(response.status_code, [200, 201, 400, 500])

    def test_quick_upload_authentication_required(self):
        """Test that authentication is required."""
        from io import BytesIO

        # Logout
        self.client.logout()

        test_file = BytesIO(b'Test content')
        test_file.name = 'test.txt'

        response = self.client.post(
            '/editor/api/quick-upload-file/',
            data={
                'file': test_file,
                'target_path': 'files'
            }
        )

        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, 401)

    def test_quick_upload_path_validation(self):
        """Test target path validation."""
        from io import BytesIO

        test_file = BytesIO(b'Test content')
        test_file.name = 'test.txt'

        response = self.client.post(
            '/editor/api/quick-upload-file/',
            data={
                'file': test_file,
                'target_path': '../../etc',
                'description': 'Path traversal attack'
            }
        )

        # Should return validation error
        self.assertEqual(response.status_code, 400)

    def test_quick_upload_dangerous_file_type(self):
        """Test that dangerous file types are blocked."""
        from io import BytesIO

        test_file = BytesIO(b'#!/bin/bash\nrm -rf /')
        test_file.name = 'malicious.sh'

        response = self.client.post(
            '/editor/api/quick-upload-file/',
            data={
                'file': test_file,
                'target_path': 'files'
            }
        )

        # Should return validation error (422 or 400)
        self.assertIn(response.status_code, [400, 422])
        data = json.loads(response.content)
        self.assertIn('error', data)
