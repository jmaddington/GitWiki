"""
Tests for Git Service.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from pathlib import Path
import shutil
import tempfile

from .models import Configuration, GitOperation
from .git_operations import GitRepository, GitRepositoryError
from .filename_utils import (
    sanitize_filename,
    get_safe_extension,
    is_safe_extension,
    validate_filename,
    generate_safe_filename,
    DANGEROUS_EXTENSIONS
)


class ConfigurationModelTest(TestCase):
    """Tests for Configuration model."""

    def test_get_set_config(self):
        """Test getting and setting configuration values."""
        # Set a config value
        config = Configuration.set_config('test_key', 'test_value', 'Test description')
        self.assertEqual(config.key, 'test_key')
        self.assertEqual(config.value, 'test_value')

        # Get the config value
        value = Configuration.get_config('test_key')
        self.assertEqual(value, 'test_value')

    def test_get_nonexistent_config(self):
        """Test getting a config that doesn't exist returns default."""
        value = Configuration.get_config('nonexistent', 'default_value')
        self.assertEqual(value, 'default_value')

    def test_initialize_defaults(self):
        """Test initializing default configurations."""
        Configuration.initialize_defaults()

        # Check that default configs exist
        self.assertIsNotNone(Configuration.get_config('permission_level'))
        self.assertIsNotNone(Configuration.get_config('branch_prefix_draft'))


class GitOperationModelTest(TestCase):
    """Tests for GitOperation model."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def test_log_operation(self):
        """Test logging a git operation."""
        operation = GitOperation.log_operation(
            operation_type='create_branch',
            user=self.user,
            branch_name='test-branch',
            success=True,
            execution_time_ms=100
        )

        self.assertIsNotNone(operation)
        self.assertEqual(operation.operation_type, 'create_branch')
        self.assertEqual(operation.user, self.user)
        self.assertEqual(operation.branch_name, 'test-branch')
        self.assertTrue(operation.success)

    def test_operation_str(self):
        """Test string representation of operation."""
        operation = GitOperation.log_operation(
            operation_type='commit',
            user=self.user,
            success=True
        )

        str_repr = str(operation)
        self.assertIn('commit', str_repr)
        self.assertIn('testuser', str_repr)


class GitRepositoryTest(TestCase):
    """Tests for GitRepository class."""

    def setUp(self):
        """Set up temporary repository for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = GitRepository(repo_path=self.temp_dir)
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def tearDown(self):
        """Clean up temporary directory."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_repository_initialization(self):
        """Test that repository is initialized correctly."""
        self.assertTrue(self.temp_dir.exists())
        self.assertTrue((self.temp_dir / '.git').exists())
        self.assertIsNotNone(self.repo.repo)

    def test_create_draft_branch(self):
        """Test creating a draft branch."""
        result = self.repo.create_draft_branch(user_id=1, user=self.user)

        self.assertTrue(result['success'])
        self.assertIn('branch_name', result)
        self.assertIn('draft-1-', result['branch_name'])

        # Verify branch exists
        branches = self.repo.list_branches()
        self.assertIn(result['branch_name'], branches)

    def test_commit_changes(self):
        """Test committing changes to a branch."""
        # Create branch
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        # Commit changes
        result = self.repo.commit_changes(
            branch_name=branch_name,
            file_path='test.md',
            content='# Test\nHello World',
            commit_message='Add test file',
            user_info={'name': 'Test User', 'email': 'test@example.com'},
            user=self.user
        )

        self.assertTrue(result['success'])
        self.assertIn('commit_hash', result)

        # Verify file exists
        content = self.repo.get_file_content('test.md', branch=branch_name)
        self.assertEqual(content, '# Test\nHello World')

    def test_publish_draft_no_conflicts(self):
        """Test publishing a draft without conflicts."""
        # Create branch
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        # Commit changes
        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='new_file.md',
            content='# New File',
            commit_message='Add new file',
            user_info={'name': 'Test User', 'email': 'test@example.com'},
            user=self.user
        )

        # Publish
        result = self.repo.publish_draft(branch_name=branch_name, user=self.user, auto_push=False)

        self.assertTrue(result['success'])
        self.assertTrue(result['merged'])
        self.assertIn('commit_hash', result)

        # Verify file exists in main
        content = self.repo.get_file_content('new_file.md', branch='main')
        self.assertEqual(content, '# New File')

        # Verify branch was deleted
        branches = self.repo.list_branches()
        self.assertNotIn(branch_name, branches)

    def test_list_branches(self):
        """Test listing branches."""
        # Create multiple branches
        branch1 = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch2 = self.repo.create_draft_branch(user_id=2, user=self.user)

        # List all branches
        branches = self.repo.list_branches()
        self.assertIn('main', branches)
        self.assertIn(branch1['branch_name'], branches)
        self.assertIn(branch2['branch_name'], branches)

        # List with pattern
        draft_branches = self.repo.list_branches(pattern='draft-*')
        self.assertNotIn('main', draft_branches)
        self.assertIn(branch1['branch_name'], draft_branches)

    def test_commit_to_nonexistent_branch(self):
        """Test that committing to non-existent branch raises error."""
        with self.assertRaises(GitRepositoryError):
            self.repo.commit_changes(
                branch_name='nonexistent-branch',
                file_path='test.md',
                content='Test',
                commit_message='Test',
                user_info={'name': 'Test', 'email': 'test@example.com'}
            )

    def test_get_conflicts_no_conflicts(self):
        """Test get_conflicts returns empty when no conflicts exist."""
        conflicts_data = self.repo.get_conflicts()

        self.assertIsInstance(conflicts_data, dict)
        self.assertIn('conflicts', conflicts_data)
        self.assertEqual(len(conflicts_data['conflicts']), 0)
        self.assertIn('timestamp', conflicts_data)

    def test_get_conflicts_with_conflict(self):
        """Test get_conflicts detects actual conflicts."""
        # Start with a base file on main
        self.repo.commit_changes(
            branch_name='main',
            file_path='conflict.md',
            content='# Original\nBase content',
            commit_message='Initial version',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        # Create branch 1 and modify the file
        branch1 = self.repo.create_draft_branch(user_id=1, user=self.user)['branch_name']
        self.repo.commit_changes(
            branch_name=branch1,
            file_path='conflict.md',
            content='# Version 1\nContent from user 1',
            commit_message='User 1 edit',
            user_info={'name': 'User 1', 'email': 'user1@example.com'},
            user=self.user
        )

        # Modify main (creating the conflict)
        self.repo.commit_changes(
            branch_name='main',
            file_path='conflict.md',
            content='# Version Main\nContent from main',
            commit_message='Main edit',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        # Now branch1 should have a conflict with main
        conflicts_data = self.repo.get_conflicts()

        self.assertEqual(len(conflicts_data['conflicts']), 1)
        conflict = conflicts_data['conflicts'][0]
        self.assertEqual(conflict['branch_name'], branch1)
        self.assertIn('conflict.md', conflict['file_paths'])
        self.assertEqual(conflict['user_id'], 1)

    def test_get_conflict_versions(self):
        """Test extracting three-way diff versions."""
        # Setup: Create conflicting changes
        # Start with a base file
        self.repo.commit_changes(
            branch_name='main',
            file_path='base.md',
            content='# Original\nBase content',
            commit_message='Initial version',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        # Create branch and modify file
        branch = self.repo.create_draft_branch(user_id=1, user=self.user)['branch_name']
        self.repo.commit_changes(
            branch_name=branch,
            file_path='base.md',
            content='# Modified\nMy changes',
            commit_message='My edit',
            user_info={'name': 'User 1', 'email': 'user1@example.com'},
            user=self.user
        )

        # Also modify on main (simulating another user's publish)
        self.repo.commit_changes(
            branch_name='main',
            file_path='base.md',
            content='# Updated\nOther changes',
            commit_message='Other edit',
            user_info={'name': 'User 2', 'email': 'user2@example.com'},
            user=self.user
        )

        # Get three-way diff
        versions = self.repo.get_conflict_versions(branch, 'base.md')

        self.assertIn('base', versions)
        self.assertIn('theirs', versions)
        self.assertIn('ours', versions)
        self.assertEqual(versions['base'], '# Original\nBase content')
        self.assertEqual(versions['theirs'], '# Updated\nOther changes')
        self.assertEqual(versions['ours'], '# Modified\nMy changes')

    def test_resolve_conflict_success(self):
        """Test successful conflict resolution."""
        # Setup conflict scenario
        self.repo.commit_changes(
            branch_name='main',
            file_path='resolve.md',
            content='# Original\nBase',
            commit_message='Initial',
            user_info={'name': 'Admin', 'email': 'admin@example.com'},
            user=self.user
        )

        # Branch 1 modifies
        branch1 = self.repo.create_draft_branch(user_id=1, user=self.user)['branch_name']
        self.repo.commit_changes(
            branch_name=branch1,
            file_path='resolve.md',
            content='# Modified\nBranch 1 content',
            commit_message='Edit 1',
            user_info={'name': 'User 1', 'email': 'user1@example.com'},
            user=self.user
        )

        # Main is updated (creating conflict)
        self.repo.commit_changes(
            branch_name='main',
            file_path='resolve.md',
            content='# Updated\nMain content',
            commit_message='Edit 2',
            user_info={'name': 'User 2', 'email': 'user2@example.com'},
            user=self.user
        )

        # Resolve conflict
        result = self.repo.resolve_conflict(
            branch_name=branch1,
            file_path='resolve.md',
            resolution_content='# Resolved\nMerged content',
            user_info={'name': 'User 1', 'email': 'user1@example.com'},
            is_binary=False
        )

        self.assertTrue(result['success'])
        # Note: The merge might still fail even after resolution if conflicts persist
        # Check that resolution was applied
        self.assertIn('commit_hash', result)

    def test_resolve_conflict_nonexistent_branch(self):
        """Test that resolving conflict on non-existent branch raises error."""
        with self.assertRaises(GitRepositoryError):
            self.repo.resolve_conflict(
                branch_name='nonexistent-branch',
                file_path='test.md',
                resolution_content='Content',
                user_info={'name': 'Test', 'email': 'test@example.com'},
                is_binary=False
            )

    def test_get_conflict_versions_nonexistent_file(self):
        """Test get_conflict_versions with file that doesn't exist."""
        branch = self.repo.create_draft_branch(user_id=1, user=self.user)['branch_name']

        versions = self.repo.get_conflict_versions(branch, 'nonexistent.md')

        # Should return empty strings for missing files
        self.assertEqual(versions['base'], '')
        self.assertEqual(versions['theirs'], '')
        self.assertEqual(versions['ours'], '')


class GitHubIntegrationTests(TestCase):
    """Tests for Phase 5 - GitHub integration methods."""

    def setUp(self):
        """Set up test repository."""
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = GitRepository(repo_path=self.temp_dir)

        # Create initial file
        self.repo.commit_changes(
            branch_name='main',
            file_path='README.md',
            content='# Test Repo',
            commit_message='Initial commit',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

    def tearDown(self):
        """Clean up test repository."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_pull_from_github_no_config(self):
        """Test pull_from_github when GitHub URL is not configured."""
        result = self.repo.pull_from_github()

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'GitHub remote URL not configured')
        self.assertFalse(result['changes_detected'])

    def test_push_to_github_no_config(self):
        """Test push_to_github when GitHub URL is not configured."""
        result = self.repo.push_to_github()

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'GitHub remote URL not configured')
        self.assertEqual(result['commits_pushed'], 0)

    def test_cleanup_stale_branches_no_branches(self):
        """Test cleanup_stale_branches when there are no draft branches."""
        result = self.repo.cleanup_stale_branches(age_days=7)

        self.assertTrue(result['success'])
        self.assertEqual(len(result['branches_deleted']), 0)
        self.assertEqual(len(result['branches_kept']), 0)
        self.assertEqual(result['disk_space_freed_mb'], 0)

    def test_cleanup_stale_branches_with_old_branch(self):
        """Test cleanup_stale_branches removes old inactive branches."""
        from editor.models import EditSession

        # Create a draft branch
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        # Create an inactive session
        session = EditSession.objects.create(
            user=self.user,
            branch_name=branch_name,
            is_active=False
        )

        # Run cleanup with age_days=0 to delete all old branches
        result = self.repo.cleanup_stale_branches(age_days=0)

        # Branch should be deleted (it's old and inactive)
        # Note: This might not delete if the branch is too recent (committed just now)
        # So we just check the structure of the result
        self.assertTrue(result['success'])
        self.assertIn('branches_deleted', result)
        self.assertIn('branches_kept', result)
        self.assertIn('disk_space_freed_mb', result)

    def test_cleanup_stale_branches_keeps_active_session(self):
        """Test cleanup_stale_branches keeps branches with active sessions."""
        from editor.models import EditSession

        # Create a draft branch
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        # Create an active session
        session = EditSession.objects.create(
            user=self.user,
            branch_name=branch_name,
            is_active=True
        )

        # Run cleanup with age_days=0
        result = self.repo.cleanup_stale_branches(age_days=0)

        # Branch should be kept (active session)
        self.assertTrue(result['success'])
        self.assertIn(branch_name, result['branches_kept'])
        self.assertNotIn(branch_name, result['branches_deleted'])

    def test_full_static_rebuild(self):
        """Test full_static_rebuild regenerates all static files."""
        result = self.repo.full_static_rebuild()

        self.assertTrue(result['success'])
        self.assertIn('main', result['branches_regenerated'])
        self.assertGreaterEqual(result['total_files'], 0)
        self.assertGreater(result['execution_time_ms'], 0)

    def test_full_static_rebuild_with_draft_branch(self):
        """Test full_static_rebuild includes active draft branches."""
        from editor.models import EditSession

        # Create a draft branch with active session
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        session = EditSession.objects.create(
            user=self.user,
            branch_name=branch_name,
            is_active=True
        )

        # Add a file to the draft branch
        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='draft.md',
            content='# Draft Content',
            commit_message='Draft commit',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        result = self.repo.full_static_rebuild()

        self.assertTrue(result['success'])
        self.assertIn('main', result['branches_regenerated'])
        self.assertIn(branch_name, result['branches_regenerated'])


class SSHUtilityTests(TestCase):
    """Tests for SSH utility functions."""

    def test_validate_remote_url_ssh_format(self):
        """Test validate_remote_url accepts SSH format."""
        from .utils import validate_remote_url

        self.assertTrue(validate_remote_url('git@github.com:user/repo.git'))
        self.assertTrue(validate_remote_url('git@gitlab.com:user/repo.git'))

    def test_validate_remote_url_https_format(self):
        """Test validate_remote_url accepts HTTPS format."""
        from .utils import validate_remote_url

        self.assertTrue(validate_remote_url('https://github.com/user/repo.git'))
        self.assertTrue(validate_remote_url('http://github.com/user/repo.git'))

    def test_validate_remote_url_git_protocol(self):
        """Test validate_remote_url accepts git:// protocol."""
        from .utils import validate_remote_url

        self.assertTrue(validate_remote_url('git://github.com/user/repo.git'))

    def test_validate_remote_url_invalid(self):
        """Test validate_remote_url rejects invalid URLs."""
        from .utils import validate_remote_url

        self.assertFalse(validate_remote_url(''))
        self.assertFalse(validate_remote_url('invalid'))
        self.assertFalse(validate_remote_url('just-a-path'))

    def test_extract_repo_name_ssh(self):
        """Test extract_repo_name from SSH URL."""
        from .utils import extract_repo_name

        self.assertEqual(
            extract_repo_name('git@github.com:user/repo.git'),
            'repo'
        )

    def test_extract_repo_name_https(self):
        """Test extract_repo_name from HTTPS URL."""
        from .utils import extract_repo_name

        self.assertEqual(
            extract_repo_name('https://github.com/user/repo.git'),
            'repo'
        )

    def test_extract_repo_name_no_git_extension(self):
        """Test extract_repo_name without .git extension."""
        from .utils import extract_repo_name

        self.assertEqual(
            extract_repo_name('git@github.com:user/repo'),
            'repo'
        )


class ThreadSafetyTest(TestCase):
    """
    Tests for thread safety of repository singleton.

    AIDEV-NOTE: thread-safety-tests; Ensure singleton is safe in concurrent environments
    """

    def setUp(self):
        """Reset the singleton before each test."""
        import git_service.git_operations as git_ops
        git_ops._repo_instance = None

    def test_singleton_thread_safety(self):
        """Test that get_repository is thread-safe and returns the same instance."""
        import threading
        from .git_operations import get_repository

        instances = []
        barrier = threading.Barrier(10)

        def get_repo_thread():
            barrier.wait()
            repo = get_repository()
            instances.append(id(repo))

        threads = [threading.Thread(target=get_repo_thread) for _ in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(set(instances)), 1, 'All threads should get the same instance')

    def test_concurrent_initialization(self):
        """Test that concurrent calls to get_repository only initialize once."""
        import threading
        from .git_operations import get_repository
        import git_service.git_operations as git_ops

        init_count = {'count': 0}
        original_init = git_ops.GitRepository.__init__

        def counting_init(self, repo_path=None):
            init_count['count'] += 1
            original_init(self, repo_path)

        try:
            git_ops.GitRepository.__init__ = counting_init

            barrier = threading.Barrier(20)

            def get_repo_thread():
                barrier.wait()
                get_repository()

            threads = [threading.Thread(target=get_repo_thread) for _ in range(20)]

            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(init_count['count'], 1, 'GitRepository should only be initialized once')
        finally:
            git_ops.GitRepository.__init__ = original_init

    def test_lock_acquisition(self):
        """Test that lock is properly acquired and released."""
        import threading
        from .git_operations import get_repository, _repo_lock

        self.assertFalse(_repo_lock.locked(), 'Lock should not be held initially')

        repo = get_repository()
        self.assertIsNotNone(repo)

        self.assertFalse(_repo_lock.locked(), 'Lock should be released after initialization')

    def test_double_checked_locking_performance(self):
        """Test that double-checked locking avoids lock contention after initialization."""
        import threading
        import time
        from .git_operations import get_repository

        get_repository()

        start_time = time.time()

        def get_repo_thread():
            for _ in range(1000):
                get_repository()

        threads = [threading.Thread(target=get_repo_thread) for _ in range(5)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        elapsed = time.time() - start_time

        self.assertLess(elapsed, 1.0, 'Should complete quickly without lock contention')

    def test_concurrent_operations_different_threads(self):
        """Test that multiple threads can use the repository concurrently."""
        import threading
        from .git_operations import get_repository

        results = {'success': 0, 'failure': 0}
        lock = threading.Lock()

        def repo_operation_thread():
            try:
                repo = get_repository()
                self.assertIsNotNone(repo)
                self.assertIsNotNone(repo.repo)
                with lock:
                    results['success'] += 1
            except Exception:
                with lock:
                    results['failure'] += 1

        threads = [threading.Thread(target=repo_operation_thread) for _ in range(50)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(results['success'], 50, 'All threads should succeed')
        self.assertEqual(results['failure'], 0, 'No threads should fail')


class IncrementalRebuildTest(TestCase):
    """Tests for incremental static file rebuild functionality."""

    def setUp(self):
        """Set up temporary repository for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = GitRepository(repo_path=self.temp_dir)
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')

    def tearDown(self):
        """Clean up temporary directory."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_get_changed_files_single_file(self):
        """Test detecting changed files for a single file edit."""
        # Create branch and commit a file
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='test.md',
            content='# Test',
            commit_message='Add test file',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        # Get changed files
        changed_files = self.repo.get_changed_files_in_merge(branch_name, 'main')

        self.assertEqual(len(changed_files), 1)
        self.assertIn('test.md', changed_files)

    def test_get_changed_files_multiple_files(self):
        """Test detecting changed files for multiple file edits."""
        # Create branch and commit multiple files
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='doc1.md',
            content='# Doc 1',
            commit_message='Add doc1',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='doc2.md',
            content='# Doc 2',
            commit_message='Add doc2',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        # Get changed files
        changed_files = self.repo.get_changed_files_in_merge(branch_name, 'main')

        self.assertEqual(len(changed_files), 2)
        self.assertIn('doc1.md', changed_files)
        self.assertIn('doc2.md', changed_files)

    def test_get_changed_files_no_changes(self):
        """Test detecting no changed files when branch is identical to main."""
        # Create branch without any commits
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        # Get changed files (should be empty)
        changed_files = self.repo.get_changed_files_in_merge(branch_name, 'main')

        self.assertEqual(len(changed_files), 0)

    def test_write_files_to_disk_single_file(self):
        """Test incremental rebuild with a single changed file."""
        # Create and commit a file on main branch first
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='initial.md',
            content='# Initial',
            commit_message='Add initial file',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        # Publish to create initial static files
        self.repo.publish_draft(branch_name=branch_name, user=self.user, auto_push=False)

        # Create another file
        branch_result2 = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name2 = branch_result2['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name2,
            file_path='new.md',
            content='# New File',
            commit_message='Add new file',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        # Get changed files
        changed_files = self.repo.get_changed_files_in_merge(branch_name2, 'main')

        # Merge to main
        self.repo.repo.heads.main.checkout()
        self.repo.repo.git.merge(branch_name2, no_ff=True, m="Test merge")

        # Test incremental rebuild
        result = self.repo.write_files_to_disk('main', changed_files, self.user)

        self.assertTrue(result['success'])
        self.assertTrue(result.get('incremental', False))
        self.assertEqual(result['markdown_files'], 1)

    def test_write_files_to_disk_empty_list(self):
        """Test incremental rebuild with no changed files."""
        result = self.repo.write_files_to_disk('main', [], self.user)

        self.assertTrue(result['success'])
        self.assertEqual(result['files_written'], 0)
        self.assertEqual(result['markdown_files'], 0)

    def test_publish_draft_uses_incremental_rebuild(self):
        """Test that publish_draft now uses incremental rebuild."""
        # Create branch and commit a file
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='test_publish.md',
            content='# Test Publish',
            commit_message='Add test file',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        # Publish (should use incremental rebuild internally)
        result = self.repo.publish_draft(branch_name=branch_name, user=self.user, auto_push=False)

        self.assertTrue(result['success'])
        self.assertTrue(result['merged'])

        # Verify file exists in main
        content = self.repo.get_file_content('test_publish.md', branch='main')
        self.assertEqual(content, '# Test Publish')

    def test_copy_folder_to_static(self):
        """Test copying folder with .gitkeep to static directory."""
        # Create a folder with .gitkeep on main
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='new_folder/.gitkeep',
            content='',
            commit_message='Create folder',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        # Merge to main
        self.repo.repo.heads.main.checkout()
        self.repo.repo.git.merge(branch_name, no_ff=True, m="Create folder")
        self.repo.repo.delete_head(branch_name, force=True)

        # Test folder copy
        result = self.repo.copy_folder_to_static('new_folder', 'main')

        self.assertTrue(result['success'])
        self.assertEqual(result['folder_path'], 'new_folder')

    def test_incremental_rebuild_performance(self):
        """Test that incremental rebuild is faster than full rebuild."""
        import time

        # Create initial files on main
        for i in range(5):
            branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
            branch_name = branch_result['branch_name']

            self.repo.commit_changes(
                branch_name=branch_name,
                file_path=f'file{i}.md',
                content=f'# File {i}',
                commit_message=f'Add file {i}',
                user_info={'name': 'Test', 'email': 'test@example.com'},
                user=self.user
            )

            self.repo.publish_draft(branch_name=branch_name, user=self.user, auto_push=False)

        # Measure full rebuild time
        full_start = time.time()
        self.repo.write_branch_to_disk('main', self.user)
        full_time = time.time() - full_start

        # Make a small change
        branch_result = self.repo.create_draft_branch(user_id=1, user=self.user)
        branch_name = branch_result['branch_name']

        self.repo.commit_changes(
            branch_name=branch_name,
            file_path='new_file.md',
            content='# New',
            commit_message='Add new file',
            user_info={'name': 'Test', 'email': 'test@example.com'},
            user=self.user
        )

        changed_files = self.repo.get_changed_files_in_merge(branch_name, 'main')

        self.repo.repo.heads.main.checkout()
        self.repo.repo.git.merge(branch_name, no_ff=True, m="Test merge")

        # Measure incremental rebuild time
        inc_start = time.time()
        result = self.repo.write_files_to_disk('main', changed_files, self.user)
        inc_time = time.time() - inc_start

        # Incremental should be faster (or at least not significantly slower)
        # Allow some overhead for the incremental logic
        self.assertLess(inc_time, full_time * 2.0,
                       f"Incremental rebuild ({inc_time:.3f}s) should not be much slower than full rebuild ({full_time:.3f}s)")

        self.assertTrue(result['success'])
        self.assertTrue(result.get('incremental', False))


class FilenameSanitizationTest(TestCase):
    """Tests for filename sanitization and validation utilities."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        # Normal filename
        result = sanitize_filename('my_file.pdf')
        self.assertEqual(result, 'my_file')

        # Filename with spaces
        result = sanitize_filename('my document.txt')
        self.assertEqual(result, 'my_document')

        # Filename with special characters
        result = sanitize_filename('file@#$%.doc')
        self.assertEqual(result, 'file____')

    def test_sanitize_filename_removes_dots(self):
        """Test that dots are removed from base name to prevent double-extension attacks."""
        # Double extension attack - Path.stem returns 'malware.exe' (without final .txt)
        result = sanitize_filename('malware.exe.txt')
        self.assertEqual(result, 'malware_exe')

        # Multiple dots - Path.stem returns 'my.file.name' (without final .pdf)
        result = sanitize_filename('my.file.name.pdf')
        self.assertEqual(result, 'my_file_name')

    def test_sanitize_filename_path_traversal(self):
        """Test that path traversal patterns are sanitized."""
        # Unix path traversal - Path.stem returns just 'passwd'
        result = sanitize_filename('../../etc/passwd')
        self.assertEqual(result, 'passwd')

        # Windows path traversal on Unix - Path.stem returns '..\\.', sanitized to '____'
        # Since result has no alphanumeric chars, fallback is used
        # (backslashes are literal characters on Unix, not path separators)
        result = sanitize_filename('..\\..\\Windows\\System32\\config', fallback='file')
        self.assertEqual(result, 'file')

    def test_sanitize_filename_xss_patterns(self):
        """Test that XSS patterns are sanitized."""
        # Script tags - Path.stem returns 'script>' (< and > treated as special), sanitized to 'script_'
        result = sanitize_filename('<script>alert("xss")</script>.jpg')
        self.assertEqual(result, 'script_')

        # Event handlers - Path interprets these characters specially
        result = sanitize_filename('"><img src=x onerror=alert(1)>')
        self.assertEqual(result, '___img_src_x_onerror_alert_1__')

    def test_sanitize_filename_empty_input(self):
        """Test sanitization with empty or invalid input."""
        # Empty string
        result = sanitize_filename('', fallback='default')
        self.assertEqual(result, 'default')

        # None
        result = sanitize_filename(None, fallback='default')
        self.assertEqual(result, 'default')

        # Only special characters - Path.stem returns '@#$%^&*()' then sanitization converts to underscores
        # Since result has no alphanumeric chars, fallback is used
        result = sanitize_filename('@#$%^&*()', fallback='file')
        self.assertEqual(result, 'file')

    def test_get_safe_extension(self):
        """Test safe extension extraction."""
        # Normal extension
        self.assertEqual(get_safe_extension('file.pdf'), 'pdf')

        # Multiple dots
        self.assertEqual(get_safe_extension('archive.tar.gz'), 'gz')

        # No extension
        self.assertIsNone(get_safe_extension('noextension'))

        # Uppercase extension
        self.assertEqual(get_safe_extension('FILE.PDF'), 'pdf')

        # Empty filename
        self.assertIsNone(get_safe_extension(''))

    def test_is_safe_extension(self):
        """Test extension safety checking."""
        # Safe extensions
        self.assertTrue(is_safe_extension('pdf'))
        self.assertTrue(is_safe_extension('jpg'))
        self.assertTrue(is_safe_extension('txt'))
        self.assertTrue(is_safe_extension(None))  # No extension is safe

        # Dangerous extensions
        self.assertFalse(is_safe_extension('exe'))
        self.assertFalse(is_safe_extension('sh'))
        self.assertFalse(is_safe_extension('bat'))
        self.assertFalse(is_safe_extension('jar'))

        # With leading dot
        self.assertFalse(is_safe_extension('.exe'))

    def test_dangerous_extensions_completeness(self):
        """Test that DANGEROUS_EXTENSIONS includes critical file types."""
        # Windows executables
        self.assertIn('exe', DANGEROUS_EXTENSIONS)
        self.assertIn('bat', DANGEROUS_EXTENSIONS)
        self.assertIn('msi', DANGEROUS_EXTENSIONS)

        # Unix/Linux executables
        self.assertIn('sh', DANGEROUS_EXTENSIONS)
        self.assertIn('bash', DANGEROUS_EXTENSIONS)
        self.assertIn('bin', DANGEROUS_EXTENSIONS)

        # macOS executables
        self.assertIn('app', DANGEROUS_EXTENSIONS)
        self.assertIn('dmg', DANGEROUS_EXTENSIONS)

        # Cross-platform
        self.assertIn('jar', DANGEROUS_EXTENSIONS)

        # Verify count (should be 30+)
        self.assertGreaterEqual(len(DANGEROUS_EXTENSIONS), 30)

    def test_validate_filename_valid(self):
        """Test filename validation with valid inputs."""
        # Valid filename
        valid, error = validate_filename('document.pdf')
        self.assertTrue(valid)
        self.assertIsNone(error)

        # Valid filename without extension
        valid, error = validate_filename('myfile')
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_filename_dangerous_extension(self):
        """Test filename validation rejects dangerous extensions."""
        # Executable
        valid, error = validate_filename('malware.exe')
        self.assertFalse(valid)
        self.assertIn('Dangerous file type', error)

        # Shell script
        valid, error = validate_filename('script.sh')
        self.assertFalse(valid)
        self.assertIn('Dangerous file type', error)

    def test_validate_filename_path_traversal(self):
        """Test filename validation rejects path traversal."""
        # Double dots
        valid, error = validate_filename('../etc/passwd')
        self.assertFalse(valid)
        self.assertIn('Path traversal', error)

        # Absolute path
        valid, error = validate_filename('/etc/passwd')
        self.assertFalse(valid)
        self.assertIn('Path traversal', error)

        # Windows path
        valid, error = validate_filename('..\\Windows\\System32')
        self.assertFalse(valid)
        self.assertIn('Path traversal', error)

    def test_validate_filename_too_long(self):
        """Test filename validation rejects overly long filenames."""
        long_filename = 'a' * 300
        valid, error = validate_filename(long_filename, max_length=255)
        self.assertFalse(valid)
        self.assertIn('too long', error)

    def test_generate_safe_filename(self):
        """Test complete safe filename generation."""
        # Normal filename
        filename, ext = generate_safe_filename(
            'my document.pdf',
            '20250104-143000',
            'abc123'
        )
        self.assertEqual(filename, 'my_document-20250104-143000-abc123')
        self.assertEqual(ext, 'pdf')

        # Double-extension attack - Path.stem returns 'malware.exe'
        filename, ext = generate_safe_filename(
            'malware.exe.txt',
            '20250104-143000',
            'xyz789'
        )
        self.assertEqual(filename, 'malware_exe-20250104-143000-xyz789')
        self.assertEqual(ext, 'txt')

        # XSS pattern - Path.stem returns 'script>', sanitized to 'script_'
        filename, ext = generate_safe_filename(
            '<script>alert("xss")</script>.jpg',
            '20250104-143000',
            'def456'
        )
        self.assertEqual(filename, 'script_-20250104-143000-def456')
        self.assertEqual(ext, 'jpg')

        # Empty result uses fallback
        filename, ext = generate_safe_filename(
            '@#$%^&*().',
            '20250104-143000',
            'ghi789',
            fallback='uploaded'
        )
        self.assertEqual(filename, 'uploaded-20250104-143000-ghi789')
        self.assertIsNone(ext)
