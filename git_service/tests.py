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
