"""
Git operations module for GitWiki.

This module handles all Git repository operations including:
- Branch creation and management
- Commit operations
- Merge operations
- Conflict detection
- Static file generation

AIDEV-NOTE: atomic-ops; All operations must be atomic and rollback-safe
"""

import os
import shutil
import uuid
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import git
from git import Repo, GitCommandError
from django.conf import settings
from django.contrib.auth.models import User
import logging

from .models import Configuration, GitOperation

logger = logging.getLogger(__name__)


class GitRepositoryError(Exception):
    """Custom exception for Git repository operations."""
    pass


class GitRepository:
    """
    Manages Git repository operations for GitWiki.

    AIDEV-NOTE: repo-singleton; Single instance manages all git operations
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize Git repository manager.

        Args:
            repo_path: Path to Git repository (defaults to settings.WIKI_REPO_PATH)
        """
        self.repo_path = repo_path or settings.WIKI_REPO_PATH
        self.repo = None
        self._initialize_repository()

    def _initialize_repository(self):
        """Initialize or load existing Git repository."""
        try:
            git_dir = self.repo_path / '.git'

            if not git_dir.exists():
                logger.info(f'Creating new repository at {self.repo_path} [GITREPO-INIT01]')
                self.repo_path.mkdir(parents=True, exist_ok=True)
                self.repo = Repo.init(self.repo_path)

                # Disable GPG signing for this repository
                with self.repo.config_writer() as config:
                    config.set_value('commit', 'gpgsign', 'false')
                    config.set_value('tag', 'gpgsign', 'false')

                # Create initial commit
                readme_path = self.repo_path / "README.md"
                readme_path.write_text("# GitWiki\n\nWelcome to GitWiki!\n")
                self.repo.index.add([str(readme_path)])
                self.repo.index.commit("Initial commit")
                logger.info('Repository initialized with initial commit [GITREPO-INIT02]')
            else:
                logger.info(f'Loading existing repository at {self.repo_path} [GITREPO-LOAD01]')
                self.repo = Repo(self.repo_path)

            # Ensure we're on main branch
            if not self._has_branch('main'):
                logger.info('Creating main branch [GITREPO-MAIN01]')
                if self.repo.heads:
                    self.repo.heads[0].rename('main')

        except Exception as e:
            logger.error(f'Failed to initialize repository: {str(e)} [GITREPO-INIT03]')
            raise GitRepositoryError(f"Failed to initialize repository: {str(e)}")

    def _has_branch(self, branch_name: str) -> bool:
        """Check if branch exists."""
        try:
            return branch_name in [head.name for head in self.repo.heads]
        except Exception:
            return False

    def _generate_branch_name(self, user_id: int) -> str:
        """
        Generate unique draft branch name.

        Args:
            user_id: User ID

        Returns:
            Branch name in format: draft-{user_id}-{uuid}
        """
        prefix = Configuration.get_config('branch_prefix_draft', 'draft')
        uuid_fragment = str(uuid.uuid4())[:8]
        return f"{prefix}-{user_id}-{uuid_fragment}"

    def create_draft_branch(self, user_id: int, user: Optional[User] = None) -> Dict:
        """
        Create a new draft branch for user editing.

        Args:
            user_id: User ID
            user: Optional User instance for logging

        Returns:
            Dict with branch_name and success status

        Raises:
            GitRepositoryError: If branch creation fails
        """
        start_time = time.time()
        branch_name = self._generate_branch_name(user_id)

        try:
            # Ensure we're on main branch
            self.repo.heads.main.checkout()

            # Create new branch from main
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            execution_time = int((time.time() - start_time) * 1000)

            # Log operation
            GitOperation.log_operation(
                operation_type='create_branch',
                user=user,
                branch_name=branch_name,
                request_params={'user_id': user_id},
                response_code=200,
                success=True,
                git_output=f'Created branch {branch_name}',
                execution_time_ms=execution_time
            )

            logger.info(f'Created draft branch: {branch_name} [GITOPS-BRANCH01]')

            return {
                'success': True,
                'branch_name': branch_name
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f'Failed to create branch: {str(e)}'

            GitOperation.log_operation(
                operation_type='create_branch',
                user=user,
                branch_name=branch_name,
                request_params={'user_id': user_id},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time
            )

            logger.error(f'{error_msg} [GITOPS-BRANCH02]')
            raise GitRepositoryError(error_msg)

    def commit_changes(
        self,
        branch_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        user_info: Dict[str, str],
        user: Optional[User] = None
    ) -> Dict:
        """
        Commit changes to a draft branch.

        Args:
            branch_name: Name of the draft branch
            file_path: Relative path to file in repository
            content: File content
            commit_message: Commit message
            user_info: Dict with 'name' and 'email' keys
            user: Optional User instance for logging

        Returns:
            Dict with commit_hash and success status

        Raises:
            GitRepositoryError: If commit fails
        """
        start_time = time.time()

        try:
            # Validate branch exists
            if not self._has_branch(branch_name):
                raise GitRepositoryError(f"Branch {branch_name} does not exist")

            # Checkout branch
            self.repo.heads[branch_name].checkout()

            # Write file content
            full_path = self.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')

            # Stage file
            self.repo.index.add([file_path])

            # Configure author
            actor = git.Actor(user_info.get('name', 'Unknown'), user_info.get('email', 'unknown@example.com'))

            # Commit
            commit = self.repo.index.commit(commit_message, author=actor, committer=actor)
            commit_hash = commit.hexsha

            execution_time = int((time.time() - start_time) * 1000)

            # Log operation
            GitOperation.log_operation(
                operation_type='commit',
                user=user,
                branch_name=branch_name,
                file_path=file_path,
                request_params={
                    'commit_message': commit_message,
                    'user_info': user_info,
                    'content_length': len(content)
                },
                response_code=200,
                success=True,
                git_output=f'Committed {commit_hash[:8]}',
                execution_time_ms=execution_time
            )

            logger.info(f'Committed changes to {branch_name}: {commit_hash[:8]} [GITOPS-COMMIT01]')

            return {
                'success': True,
                'commit_hash': commit_hash
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f'Failed to commit changes: {str(e)}'

            GitOperation.log_operation(
                operation_type='commit',
                user=user,
                branch_name=branch_name,
                file_path=file_path,
                request_params={'commit_message': commit_message},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time
            )

            logger.error(f'{error_msg} [GITOPS-COMMIT02]')
            raise GitRepositoryError(error_msg)

    def _check_merge_conflicts(self, branch_name: str) -> Tuple[bool, List[str]]:
        """
        Check if merging branch to main would cause conflicts.

        AIDEV-NOTE: dry-run-merge; Uses --no-commit to test merge without modifying repo

        Args:
            branch_name: Branch to test merge

        Returns:
            Tuple of (has_conflicts, list_of_conflicted_files)
        """
        try:
            # Save current branch
            current_branch = self.repo.active_branch.name

            # Checkout main
            self.repo.heads.main.checkout()

            try:
                # Attempt merge with no-commit flag
                self.repo.git.merge(branch_name, no_commit=True, no_ff=True)

                # If we get here, no conflicts
                # Abort the merge to keep repo clean
                self.repo.git.merge('--abort')

                # Return to original branch
                if current_branch != 'main':
                    self.repo.heads[current_branch].checkout()

                return False, []

            except GitCommandError as e:
                # Merge failed - check if it's due to conflicts
                if 'CONFLICT' in str(e):
                    # Get list of conflicted files
                    conflicts = []
                    try:
                        # Parse unmerged files
                        unmerged = self.repo.index.unmerged_blobs()
                        conflicts = list(unmerged.keys())
                    except Exception:
                        # If we can't get specific files, just note there are conflicts
                        conflicts = ['unknown']

                    # Abort the merge
                    self.repo.git.merge('--abort')

                    # Return to original branch
                    if current_branch != 'main':
                        self.repo.heads[current_branch].checkout()

                    return True, conflicts
                else:
                    # Different error, re-raise
                    self.repo.git.merge('--abort')
                    if current_branch != 'main':
                        self.repo.heads[current_branch].checkout()
                    raise

        except Exception as e:
            logger.error(f'Error checking merge conflicts: {str(e)} [GITOPS-CONFLICT01]')
            raise GitRepositoryError(f"Failed to check merge conflicts: {str(e)}")

    def publish_draft(
        self,
        branch_name: str,
        user: Optional[User] = None,
        auto_push: bool = True
    ) -> Dict:
        """
        Merge draft branch to main and optionally push to remote.

        Args:
            branch_name: Draft branch to publish
            user: Optional User instance for logging
            auto_push: Whether to automatically push to remote (default: True)

        Returns:
            Dict with merge status and conflict details if any

        Raises:
            GitRepositoryError: If operation fails
        """
        start_time = time.time()

        try:
            # Validate branch exists
            if not self._has_branch(branch_name):
                raise GitRepositoryError(f"Branch {branch_name} does not exist")

            # Check for conflicts first
            has_conflicts, conflicted_files = self._check_merge_conflicts(branch_name)

            if has_conflicts:
                execution_time = int((time.time() - start_time) * 1000)

                # Log conflict detection
                GitOperation.log_operation(
                    operation_type='merge',
                    user=user,
                    branch_name=branch_name,
                    request_params={'auto_push': auto_push},
                    response_code=409,
                    success=False,
                    error_message='Merge conflicts detected',
                    git_output=f'Conflicted files: {", ".join(conflicted_files)}',
                    execution_time_ms=execution_time
                )

                logger.warning(f'Merge conflicts detected for {branch_name} [GITOPS-PUBLISH01]')

                return {
                    'success': False,
                    'merged': False,
                    'conflicts': [
                        {
                            'file_path': f,
                            'conflict_type': 'content'
                        } for f in conflicted_files
                    ]
                }

            # No conflicts - proceed with merge
            self.repo.heads.main.checkout()

            # Merge branch using git merge command
            self.repo.git.merge(branch_name, no_ff=True, m=f"Merge {branch_name} into main")

            commit_hash = self.repo.head.commit.hexsha

            # Delete draft branch
            self.repo.delete_head(branch_name, force=True)

            execution_time = int((time.time() - start_time) * 1000)

            # Log successful merge
            GitOperation.log_operation(
                operation_type='merge',
                user=user,
                branch_name=branch_name,
                request_params={'auto_push': auto_push},
                response_code=200,
                success=True,
                git_output=f'Merged to main: {commit_hash[:8]}',
                execution_time_ms=execution_time
            )

            logger.info(f'Successfully merged {branch_name} to main [GITOPS-PUBLISH02]')

            # TODO: Trigger static file generation here
            # TODO: Push to remote if auto_push is True

            return {
                'success': True,
                'merged': True,
                'pushed': False,  # Will be True after push implementation
                'commit_hash': commit_hash
            }

        except GitRepositoryError:
            raise
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f'Failed to publish draft: {str(e)}'

            GitOperation.log_operation(
                operation_type='merge',
                user=user,
                branch_name=branch_name,
                request_params={'auto_push': auto_push},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time
            )

            logger.error(f'{error_msg} [GITOPS-PUBLISH03]')
            raise GitRepositoryError(error_msg)

    def get_file_content(self, file_path: str, branch: str = 'main') -> str:
        """
        Get content of a file from a specific branch.

        Args:
            file_path: Relative path to file
            branch: Branch name (default: 'main')

        Returns:
            File content as string

        Raises:
            GitRepositoryError: If file doesn't exist or can't be read
        """
        try:
            # Save current branch
            current_branch = self.repo.active_branch.name

            # Checkout target branch
            self.repo.heads[branch].checkout()

            # Read file
            full_path = self.repo_path / file_path
            if not full_path.exists():
                raise GitRepositoryError(f"File {file_path} not found in branch {branch}")

            content = full_path.read_text(encoding='utf-8')

            # Return to original branch
            if current_branch != branch:
                self.repo.heads[current_branch].checkout()

            return content

        except GitRepositoryError:
            raise
        except Exception as e:
            logger.error(f'Failed to read file {file_path}: {str(e)} [GITOPS-READ01]')
            raise GitRepositoryError(f"Failed to read file: {str(e)}")

    def list_branches(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all branches, optionally filtered by pattern.

        Args:
            pattern: Optional pattern to filter branches (e.g., 'draft-*')

        Returns:
            List of branch names
        """
        try:
            branches = [head.name for head in self.repo.heads]

            if pattern:
                import fnmatch
                branches = [b for b in branches if fnmatch.fnmatch(b, pattern)]

            return branches

        except Exception as e:
            logger.error(f'Failed to list branches: {str(e)} [GITOPS-LIST01]')
            return []


# Global repository instance
_repo_instance = None


def get_repository() -> GitRepository:
    """
    Get global GitRepository instance (singleton pattern).

    Returns:
        GitRepository instance
    """
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = GitRepository()
    return _repo_instance
