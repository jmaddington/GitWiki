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
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import git
from git import Repo, GitCommandError
from django.conf import settings
from django.contrib.auth.models import User
import logging
import markdown
from markdown.extensions.toc import TocExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension

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
                self.repo.index.add(["README.md"])
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
        user: Optional[User] = None,
        is_binary: bool = False
    ) -> Dict:
        """
        Commit changes to a draft branch.

        Args:
            branch_name: Name of the draft branch
            file_path: Relative path to file in repository
            content: File content (ignored if is_binary=True)
            commit_message: Commit message
            user_info: Dict with 'name' and 'email' keys
            user: Optional User instance for logging
            is_binary: If True, skip writing content (file already exists on disk)

        Returns:
            Dict with commit_hash and success status

        Raises:
            GitRepositoryError: If commit fails

        AIDEV-NOTE: binary-files; is_binary flag for images/binary files already on disk
        """
        start_time = time.time()

        try:
            # Validate branch exists
            if not self._has_branch(branch_name):
                raise GitRepositoryError(f"Branch {branch_name} does not exist")

            # Checkout branch if not already on it
            # AIDEV-NOTE: perf-cache-branch; Cache active branch name to avoid repeated git calls
            current_branch = self.repo.active_branch.name
            if current_branch != branch_name:
                self.repo.heads[branch_name].checkout()

            # Write file content (skip if binary file already on disk)
            full_path = self.repo_path / file_path
            if not is_binary:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding='utf-8')
            else:
                # Verify file exists for binary files
                if not full_path.exists():
                    raise GitRepositoryError(f"Binary file not found: {file_path}")

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

            # Invalidate caches for this file
            from config.cache_utils import invalidate_file_cache
            from django.core.cache import cache
            invalidate_file_cache(branch_name, file_path)

            # Invalidate conflicts cache since branch state changed
            cache.delete('git_conflicts_list')

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

    def delete_file(
        self,
        file_path: str,
        commit_message: str,
        user_info: Dict[str, str],
        user: Optional[User] = None,
        branch_name: str = 'main'
    ) -> Dict:
        """
        Delete a file from the repository.

        Args:
            file_path: Relative path to file in repository
            commit_message: Commit message for the deletion
            user_info: Dict with 'name' and 'email' keys
            user: Optional User instance for logging
            branch_name: Branch to delete from (defaults to 'main')

        Returns:
            Dict with commit_hash and success status

        Raises:
            GitRepositoryError: If deletion fails

        AIDEV-NOTE: file-deletion; Removes file from repository and commits the deletion
        """
        start_time = time.time()

        try:
            # Validate branch exists
            if not self._has_branch(branch_name):
                raise GitRepositoryError(f"Branch {branch_name} does not exist")

            # Check file exists
            full_path = self.repo_path / file_path
            if not full_path.exists():
                raise GitRepositoryError(f"File not found: {file_path}")

            # Checkout branch if not already on it
            # AIDEV-NOTE: perf-cache-branch; Cache active branch name to avoid repeated git calls
            current_branch = self.repo.active_branch.name
            if current_branch != branch_name:
                self.repo.heads[branch_name].checkout()

            # Remove file from filesystem
            full_path.unlink()

            # Stage deletion
            self.repo.index.remove([file_path])

            # Configure author
            actor = git.Actor(user_info.get('name', 'Unknown'), user_info.get('email', 'unknown@example.com'))

            # Commit
            commit = self.repo.index.commit(commit_message, author=actor, committer=actor)
            commit_hash = commit.hexsha

            execution_time = int((time.time() - start_time) * 1000)

            # Log operation
            GitOperation.log_operation(
                operation_type='delete',
                user=user,
                branch_name=branch_name,
                file_path=file_path,
                request_params={
                    'commit_message': commit_message,
                    'user_info': user_info
                },
                response_code=200,
                success=True,
                git_output=f'Deleted file, committed {commit_hash[:8]}',
                execution_time_ms=execution_time
            )

            logger.info(f'Deleted {file_path} from {branch_name}: {commit_hash[:8]} [GITOPS-DELETE01]')

            # Invalidate caches for this file
            from config.cache_utils import invalidate_file_cache
            from django.core.cache import cache
            invalidate_file_cache(branch_name, file_path)

            # Invalidate directory cache for parent directory
            parent_path = str(Path(file_path).parent)
            if parent_path == '.':
                parent_path = ''
            cache.delete(f'directory_listing_{branch_name}_{parent_path}')
            cache.delete(f'metadata_{branch_name}_{parent_path}')

            return {
                'success': True,
                'commit_hash': commit_hash
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f'Failed to delete file: {str(e)}'

            GitOperation.log_operation(
                operation_type='delete',
                user=user,
                branch_name=branch_name,
                file_path=file_path,
                request_params={'commit_message': commit_message},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time
            )

            logger.error(f'{error_msg} [GITOPS-DELETE02]')
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
                # Reset to undo staging changes (--no-commit doesn't create MERGE_HEAD)
                self.repo.git.reset('--hard', 'HEAD')

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
                    except Exception as ex:
                        # If we can't get specific files, just note there are conflicts
                        logger.warning(f'Failed to get unmerged blobs: {ex} [GITOPS-CONFLICT15]')
                        conflicts = ['unknown']

                    # Abort the merge (safe to use here as CONFLICT creates MERGE_HEAD)
                    try:
                        self.repo.git.merge('--abort')
                    except GitCommandError as abort_error:
                        # If abort fails, reset as fallback
                        logger.warning(f'Merge abort failed, using reset instead: {abort_error} [GITOPS-CONFLICT02]')
                        self.repo.git.reset('--hard', 'HEAD')

                    # Return to original branch
                    if current_branch != 'main':
                        self.repo.heads[current_branch].checkout()

                    return True, conflicts
                else:
                    # Different error - try abort first, fallback to reset
                    try:
                        self.repo.git.merge('--abort')
                    except GitCommandError:
                        self.repo.git.reset('--hard', 'HEAD')

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
            # Detect changed files before merge for incremental rebuild
            changed_files = self.get_changed_files_in_merge(branch_name, 'main')
            logger.info(f'Detected {len(changed_files)} changed files before merge [GITOPS-PUBLISH08]')

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

            # Trigger incremental static file generation for main branch
            try:
                # Use incremental rebuild with detected changes
                self.write_files_to_disk('main', changed_files, user)
                logger.info(f'Generated static files after merge (incremental) [GITOPS-PUBLISH04]')

                # Queue async full rebuild as safety net
                try:
                    from git_service.tasks import async_full_rebuild_task
                    async_full_rebuild_task.delay('main')
                    logger.info('Queued async full rebuild as safety net [GITOPS-PUBLISH06]')
                except Exception as task_err:
                    logger.warning(f'Could not queue async rebuild task: {str(task_err)} [GITOPS-PUBLISH07]')

                # Invalidate caches for main branch
                from config.cache_utils import invalidate_branch_cache, invalidate_search_cache
                from django.core.cache import cache
                invalidate_branch_cache('main')
                invalidate_search_cache('main')

                # Invalidate conflicts cache since main branch changed
                cache.delete('git_conflicts_list')

            except Exception as e:
                logger.warning(f'Static generation failed after merge: {str(e)} [GITOPS-PUBLISH05]')

            # TODO: Push to remote if auto_push is True (Phase 5)

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

    def get_changed_files_in_merge(self, source_branch: str, target_branch: str) -> List[str]:
        """
        Get list of files that differ between two branches.
        Used to detect which files need incremental rebuild.

        Args:
            source_branch: The branch being merged from (e.g., draft branch)
            target_branch: The branch being merged into (e.g., 'main')

        Returns:
            List of file paths that differ (e.g., ['docs/page.md', 'images/main/pic.png'])

        Raises:
            GitRepositoryError: If branches don't exist or diff fails
        """
        try:
            logger.info(f'Detecting changed files between {source_branch} and {target_branch} [GITOPS-CHANGED01]')

            # Get diff of file names only between branches
            # Using three-dot diff to get changes from common ancestor
            diff_output = self.repo.git.diff(
                f'{target_branch}...{source_branch}',
                name_only=True
            )

            # Parse output into list of paths
            if not diff_output.strip():
                logger.info(f'No files changed between branches [GITOPS-CHANGED02]')
                return []

            changed_files = [
                line.strip()
                for line in diff_output.split('\n')
                if line.strip()
            ]

            logger.info(f'Found {len(changed_files)} changed files [GITOPS-CHANGED03]')
            return changed_files

        except Exception as e:
            error_msg = f'Failed to detect changed files: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-CHANGED04]')
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

    def get_file_content_binary(self, file_path: str, branch: str = 'main') -> bytes:
        """
        Get binary content of a file from a specific branch.

        AIDEV-NOTE: binary-files-read; Read binary files (images, PDFs) without text encoding

        Args:
            file_path: Relative path to file
            branch: Branch name (default: 'main')

        Returns:
            File content as bytes

        Raises:
            GitRepositoryError: If file doesn't exist or can't be read
        """
        try:
            # Save current branch
            current_branch = self.repo.active_branch.name

            # Checkout target branch
            self.repo.heads[branch].checkout()

            # Read file as binary
            full_path = self.repo_path / file_path
            if not full_path.exists():
                raise GitRepositoryError(f"File {file_path} not found in branch {branch}")

            content = full_path.read_bytes()
            logger.info(f'Read binary file {file_path} from {branch} ({len(content)} bytes) [GITOPS-READ-BIN01]')

            # Return to original branch
            if current_branch != branch:
                self.repo.heads[current_branch].checkout()

            return content

        except GitRepositoryError:
            raise
        except Exception as e:
            logger.error(f'Failed to read binary file {file_path}: {str(e)} [GITOPS-READ-BIN02]')
            raise GitRepositoryError(f"Failed to read binary file: {str(e)}")

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

    def get_file_history(self, file_path: str, branch: str = 'main', limit: int = 50) -> Dict:
        """
        Get commit history for a specific file.

        Args:
            file_path: Relative path to file
            branch: Branch name (default: 'main')
            limit: Maximum number of commits to return

        Returns:
            Dict with file_path and commits list

        AIDEV-NOTE: file-history; Used for page history display
        """
        try:
            # Save current branch
            current_branch = self.repo.active_branch.name

            # Checkout target branch
            if branch in [head.name for head in self.repo.heads]:
                self.repo.heads[branch].checkout()
            else:
                raise GitRepositoryError(f"Branch {branch} not found")

            commits = []

            # Get commits that modified this file
            try:
                for commit in self.repo.iter_commits(paths=file_path, max_count=limit):
                    commit_data = {
                        'hash': commit.hexsha,
                        'short_hash': commit.hexsha[:8],
                        'author': commit.author.name,
                        'email': commit.author.email,
                        'date': commit.committed_datetime.isoformat(),
                        'message': commit.message.strip(),
                    }

                    # Try to get diff stats
                    try:
                        if commit.parents:
                            diffs = commit.parents[0].diff(commit, paths=file_path, create_patch=False)
                            if diffs:
                                diff = diffs[0]
                                commit_data['changes'] = {
                                    'additions': diff.diff.count(b'\n+') if hasattr(diff, 'diff') and diff.diff else 0,
                                    'deletions': diff.diff.count(b'\n-') if hasattr(diff, 'diff') and diff.diff else 0
                                }
                        else:
                            commit_data['changes'] = {'additions': 0, 'deletions': 0}
                    except Exception:
                        commit_data['changes'] = {'additions': 0, 'deletions': 0}

                    commits.append(commit_data)
            except Exception as e:
                logger.warning(f'No history found for {file_path}: {str(e)} [GITOPS-HISTORY01]')

            # Return to original branch
            if current_branch != branch:
                self.repo.heads[current_branch].checkout()

            return {
                'file_path': file_path,
                'branch': branch,
                'commits': commits,
                'total': len(commits)
            }

        except GitRepositoryError:
            raise
        except Exception as e:
            logger.error(f'Failed to get file history: {str(e)} [GITOPS-HISTORY02]')
            raise GitRepositoryError(f"Failed to get file history: {str(e)}")

    def _generate_metadata(self, file_path: str, branch: str) -> Dict:
        """
        Generate metadata for a file.

        Args:
            file_path: Relative path to file
            branch: Branch name

        Returns:
            Metadata dict
        """
        try:
            history = self.get_file_history(file_path, branch, limit=100)
            commits = history.get('commits', [])

            if not commits:
                return {
                    'file_path': file_path,
                    'branch': branch,
                    'last_commit': None,
                    'history_summary': {
                        'total_commits': 0,
                        'contributors': [],
                        'created': None,
                        'last_modified': None
                    }
                }

            # Get unique contributors
            contributors = list(set(c['author'] for c in commits))

            return {
                'file_path': file_path,
                'branch': branch,
                'last_commit': {
                    'hash': commits[0]['hash'],
                    'short_hash': commits[0]['short_hash'],
                    'author': commits[0]['author'],
                    'email': commits[0]['email'],
                    'date': commits[0]['date'],
                    'message': commits[0]['message']
                },
                'history_summary': {
                    'total_commits': len(commits),
                    'contributors': contributors,
                    'created': commits[-1]['date'] if commits else None,
                    'last_modified': commits[0]['date'] if commits else None
                }
            }

        except Exception as e:
            logger.warning(f'Failed to generate metadata for {file_path}: {str(e)} [GITOPS-META01]')
            return {
                'file_path': file_path,
                'branch': branch,
                'last_commit': None,
                'history_summary': {'total_commits': 0, 'contributors': [], 'created': None, 'last_modified': None}
            }

    def _markdown_to_html(self, content: str) -> Tuple[str, str]:
        """
        Convert markdown to HTML with table of contents, with caching.

        AIDEV-NOTE: markdown-conversion; Uses markdown library with extensions for tables, code, TOC
        AIDEV-NOTE: markdown-cache; Caches rendered HTML for 30 minutes using content hash

        Args:
            content: Markdown content

        Returns:
            Tuple of (html_content, toc_html)
        """
        from django.core.cache import cache
        import hashlib

        try:
            # Create cache key from content hash
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            cache_key = f'markdown:{content_hash}'

            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f'Markdown cache hit for hash {content_hash[:8]} [DISPLAY-CACHE07]')
                return cached_result

            # Render markdown
            md = markdown.Markdown(extensions=[
                TocExtension(title='Table of Contents', toc_depth='2-4'),
                CodeHiliteExtension(css_class='highlight', linenums=False),
                FencedCodeExtension(),
                TableExtension(),
                'nl2br',
                'sane_lists'
            ])

            html_content = md.convert(content)
            toc_html = md.toc if hasattr(md, 'toc') else ''

            result = (html_content, toc_html)

            # Cache for 30 minutes (1800 seconds)
            cache.set(cache_key, result, 1800)
            logger.debug(f'Markdown cached for hash {content_hash[:8]} [DISPLAY-CACHE08]')

            return result

        except Exception as e:
            logger.error(f'Failed to convert markdown: {str(e)} [GITOPS-MARKDOWN01]')
            return f'<p>Error rendering markdown: {str(e)}</p>', ''

    def write_branch_to_disk(self, branch_name: str = 'main', user: Optional[User] = None) -> Dict:
        """
        Export branch state to static files with HTML generation.

        Args:
            branch_name: Branch to export (default: 'main')
            user: Optional User instance for logging

        Returns:
            Dict with success status and file counts

        Raises:
            GitRepositoryError: If static generation fails

        AIDEV-NOTE: static-generation; Atomic operation using temp directory
        """
        start_time = time.time()
        temp_dir = None
        temp_moved = False

        try:
            # Save current branch
            current_branch = self.repo.active_branch.name

            # Checkout target branch
            if branch_name in [head.name for head in self.repo.heads]:
                self.repo.heads[branch_name].checkout()
            else:
                raise GitRepositoryError(f"Branch {branch_name} not found")

            # Create temp directory
            temp_uuid = str(uuid.uuid4())[:8]
            temp_dir = settings.WIKI_STATIC_PATH / f'.tmp-{temp_uuid}'
            temp_dir.mkdir(parents=True, exist_ok=True)

            files_written = 0
            markdown_files = []

            # Copy all files from repository (including hidden files like .gitkeep)
            def copy_tree(src, dst):
                """Recursively copy directory tree including hidden files."""
                nonlocal files_written
                for item in src.iterdir():
                    if item.name == '.git':
                        continue

                    rel_path = item.relative_to(self.repo_path)
                    dest_item = dst / item.name

                    if item.is_dir():
                        dest_item.mkdir(exist_ok=True)
                        copy_tree(item, dest_item)
                    else:
                        shutil.copy2(item, dest_item)
                        files_written += 1
                        # Track markdown files for HTML generation
                        if item.suffix == '.md':
                            markdown_files.append(str(rel_path))

            copy_tree(self.repo_path, temp_dir)

            # Generate HTML and metadata for markdown files
            for md_file in markdown_files:
                try:
                    # Read markdown content
                    md_path = temp_dir / md_file
                    md_content = md_path.read_text(encoding='utf-8')

                    # Convert to HTML
                    html_content, toc_html = self._markdown_to_html(md_content)

                    # Generate metadata
                    metadata = self._generate_metadata(md_file, branch_name)

                    # Write HTML file
                    html_file = md_path.with_suffix('.html')
                    html_file.write_text(html_content, encoding='utf-8')
                    files_written += 1

                    # Write metadata file
                    meta_file = md_path.with_suffix('.md.metadata')
                    metadata['toc'] = toc_html
                    meta_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
                    files_written += 1

                except Exception as e:
                    logger.warning(f'Failed to process {md_file}: {str(e)} [GITOPS-STATIC01]')

            # Atomic move to final location
            final_dir = settings.WIKI_STATIC_PATH / branch_name
            if final_dir.exists():
                try:
                    shutil.rmtree(final_dir)
                except Exception as e:
                    logger.error(f'Failed to remove existing directory {final_dir}: {str(e)} [GITOPS-STATIC05]')
                    raise GitRepositoryError(f'Failed to remove existing directory: {str(e)}')

            try:
                shutil.move(str(temp_dir), str(final_dir))
                temp_moved = True
            except Exception as e:
                logger.error(f'Failed to move {temp_dir} to {final_dir}: {str(e)} [GITOPS-STATIC06]')
                raise GitRepositoryError(f'Failed to move temp directory to final location: {str(e)}')

            # Return to original branch
            if current_branch != branch_name:
                self.repo.heads[current_branch].checkout()

            execution_time = int((time.time() - start_time) * 1000)

            # Log operation
            GitOperation.log_operation(
                operation_type='static_generation',
                user=user,
                branch_name=branch_name,
                request_params={'branch': branch_name},
                response_code=200,
                success=True,
                git_output=f'Generated {files_written} files',
                execution_time_ms=execution_time
            )

            logger.info(f'Generated static files for {branch_name}: {files_written} files [GITOPS-STATIC02]')

            return {
                'success': True,
                'branch_name': branch_name,
                'files_written': files_written,
                'markdown_files': len(markdown_files),
                'execution_time_ms': execution_time
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f'Failed to generate static files: {str(e)}'

            GitOperation.log_operation(
                operation_type='static_generation',
                user=user,
                branch_name=branch_name,
                request_params={'branch': branch_name},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time
            )

            logger.error(f'{error_msg} [GITOPS-STATIC03]')
            raise GitRepositoryError(error_msg)

        finally:
            # Guaranteed cleanup of temp directory if it wasn't successfully moved
            if temp_dir and temp_dir.exists() and not temp_moved:
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f'Cleaned up temp directory {temp_dir} [GITOPS-STATIC04]')
                except Exception as cleanup_err:
                    logger.error(f'Failed to cleanup temp directory {temp_dir}: {str(cleanup_err)} [GITOPS-STATIC04]')

    def write_files_to_disk(self, branch_name: str, changed_files: List[str], user: Optional[User] = None) -> Dict:
        """
        Incrementally regenerate only specified files to static directory.
        Falls back to full rebuild on any error.

        Args:
            branch_name: Branch to export (typically 'main')
            changed_files: List of file paths that changed (from get_changed_files_in_merge)
            user: Optional User instance for logging

        Returns:
            Dict with success status, file counts, and whether fallback occurred

        Raises:
            GitRepositoryError: If static generation fails

        AIDEV-NOTE: incremental-rebuild; Only regenerates changed files for performance
        """
        start_time = time.time()
        temp_dir = None
        temp_moved = False

        try:
            logger.info(f'Starting incremental rebuild for {len(changed_files)} changed files [GITOPS-PARTIAL01]')

            # If no files changed, nothing to do
            if not changed_files:
                logger.info('No files to rebuild [GITOPS-PARTIAL02]')
                return {
                    'success': True,
                    'branch_name': branch_name,
                    'files_written': 0,
                    'markdown_files': 0,
                    'execution_time_ms': 0,
                    'incremental': True
                }

            # Save current branch
            current_branch = self.repo.active_branch.name

            # Checkout target branch
            if branch_name in [head.name for head in self.repo.heads]:
                self.repo.heads[branch_name].checkout()
            else:
                raise GitRepositoryError(f"Branch {branch_name} not found")

            # Create temp directory
            temp_uuid = str(uuid.uuid4())[:8]
            temp_dir = settings.WIKI_STATIC_PATH / f'.tmp-{temp_uuid}'
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Get existing static directory
            final_dir = settings.WIKI_STATIC_PATH / branch_name

            files_written = 0
            markdown_files_processed = 0

            # Step 1: Copy existing static directory structure if it exists
            if final_dir.exists():
                logger.info(f'Copying existing static files from {branch_name} [GITOPS-PARTIAL03]')
                shutil.copytree(final_dir, temp_dir, dirs_exist_ok=True)
            else:
                logger.info(f'No existing static directory for {branch_name}, starting fresh [GITOPS-PARTIAL04]')

            # Step 2: Process changed files
            changed_md_files = set()
            affected_dirs = set()
            changed_images = []

            # First pass: collect changed markdown files and images
            for changed_file in changed_files:
                file_path = Path(changed_file)
                affected_dirs.add(str(file_path.parent))

                # Handle markdown files
                if file_path.suffix == '.md':
                    changed_md_files.add(changed_file)

                # Collect image files for batch processing
                elif changed_file.startswith('images/'):
                    changed_images.append(file_path.name)

            # AIDEV-NOTE: batch-git-grep; Process all images in one grep for performance
            # Handle image files - find markdown files that reference them (batched)
            if changed_images:
                logger.info(f'Finding markdown files referencing {len(changed_images)} changed images [GITOPS-PARTIAL05]')
                try:
                    # Build regex pattern for all images: (image1|image2|image3)
                    # Escape special regex characters in filenames
                    import re  # Local import for regex escaping
                    escaped_images = [re.escape(img) for img in changed_images]
                    pattern = '|'.join(escaped_images)
                    grep_result = self.repo.git.grep('-l', '-E', pattern, '--', '*.md')

                    if grep_result:
                        referencing_files = grep_result.strip().split('\n')
                        for ref_file in referencing_files:
                            if ref_file.strip():
                                changed_md_files.add(ref_file.strip())
                        logger.info(f'Found {len(referencing_files)} markdown files referencing changed images [GITOPS-PARTIAL06]')
                except git.exc.GitCommandError:
                    # No references found (grep returns error if no matches)
                    logger.info(f'No markdown files reference changed images [GITOPS-PARTIAL07]')

            # Second pass: copy changed files to temp directory
            for changed_file in changed_files:
                # Copy the changed file to temp directory
                source_path = self.repo_path / changed_file
                dest_path = temp_dir / changed_file

                if source_path.exists():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    files_written += 1
                    logger.debug(f'Copied changed file {changed_file} [GITOPS-PARTIAL08]')
                elif dest_path.exists():
                    # File was deleted in the change
                    dest_path.unlink()
                    logger.info(f'Removed deleted file {changed_file} [GITOPS-PARTIAL09]')

            # Step 3: Regenerate HTML and metadata for affected markdown files
            logger.info(f'Regenerating {len(changed_md_files)} markdown files [GITOPS-PARTIAL10]')

            for md_file in changed_md_files:
                try:
                    md_path = self.repo_path / md_file
                    if not md_path.exists():
                        # File was deleted, remove associated HTML and metadata
                        html_file = temp_dir / Path(md_file).with_suffix('.html')
                        meta_file = temp_dir / Path(md_file).with_suffix('.md.metadata')
                        if html_file.exists():
                            html_file.unlink()
                        if meta_file.exists():
                            meta_file.unlink()
                        logger.info(f'Removed HTML/metadata for deleted file {md_file} [GITOPS-PARTIAL11]')
                        continue

                    # Read markdown content
                    md_content = md_path.read_text(encoding='utf-8')

                    # Convert to HTML
                    html_content, toc_html = self._markdown_to_html(md_content)

                    # Generate metadata
                    metadata = self._generate_metadata(md_file, branch_name)

                    # Write HTML file
                    html_file = (temp_dir / md_file).with_suffix('.html')
                    html_file.parent.mkdir(parents=True, exist_ok=True)
                    html_file.write_text(html_content, encoding='utf-8')
                    files_written += 1

                    # Write metadata file
                    meta_file = (temp_dir / md_file).with_suffix('.md.metadata')
                    metadata['toc'] = toc_html
                    meta_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
                    files_written += 1

                    markdown_files_processed += 1
                    logger.debug(f'Regenerated HTML/metadata for {md_file} [GITOPS-PARTIAL12]')

                except Exception as e:
                    logger.warning(f'Failed to process {md_file}: {str(e)} [GITOPS-PARTIAL13]')

            # Step 4: Update directory listings for affected directories
            # (This could be enhanced in the future to regenerate directory index pages)
            logger.info(f'Affected directories: {len(affected_dirs)} [GITOPS-PARTIAL14]')

            # Step 5: Atomic move to final location
            if final_dir.exists():
                try:
                    shutil.rmtree(final_dir)
                except Exception as e:
                    logger.error(f'Failed to remove existing directory {final_dir}: {str(e)} [GITOPS-PARTIAL15]')
                    raise GitRepositoryError(f'Failed to remove existing directory: {str(e)}')

            try:
                shutil.move(str(temp_dir), str(final_dir))
                temp_moved = True
            except Exception as e:
                logger.error(f'Failed to move {temp_dir} to {final_dir}: {str(e)} [GITOPS-PARTIAL16]')
                raise GitRepositoryError(f'Failed to move temp directory to final location: {str(e)}')

            # Return to original branch
            if current_branch != branch_name:
                self.repo.heads[current_branch].checkout()

            execution_time = int((time.time() - start_time) * 1000)

            # Log operation
            GitOperation.log_operation(
                operation_type='incremental_static_generation',
                user=user,
                branch_name=branch_name,
                request_params={
                    'branch': branch_name,
                    'changed_files_count': len(changed_files),
                    'markdown_files_processed': markdown_files_processed
                },
                response_code=200,
                success=True,
                git_output=f'Regenerated {files_written} files ({markdown_files_processed} markdown)',
                execution_time_ms=execution_time
            )

            logger.info(f'Incremental rebuild complete: {files_written} files, {markdown_files_processed} markdown in {execution_time}ms [GITOPS-PARTIAL17]')

            return {
                'success': True,
                'branch_name': branch_name,
                'files_written': files_written,
                'markdown_files': markdown_files_processed,
                'execution_time_ms': execution_time,
                'incremental': True
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f'Incremental rebuild failed, falling back to full rebuild: {str(e)}'

            logger.warning(f'{error_msg} [GITOPS-PARTIAL18]')

            # Cleanup temp directory before fallback
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_err:
                    logger.error(f'Failed to cleanup temp directory: {str(cleanup_err)} [GITOPS-PARTIAL19]')

            # Fallback to full rebuild
            try:
                logger.info(f'Attempting full rebuild fallback [GITOPS-PARTIAL20]')
                result = self.write_branch_to_disk(branch_name, user)
                result['incremental'] = False
                result['fallback'] = True
                return result
            except Exception as fallback_error:
                final_error = f'Both incremental and full rebuild failed: {str(fallback_error)}'
                logger.error(f'{final_error} [GITOPS-PARTIAL21]')
                raise GitRepositoryError(final_error)

        finally:
            # Guaranteed cleanup of temp directory if it wasn't successfully moved
            if temp_dir and temp_dir.exists() and not temp_moved:
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f'Cleaned up temp directory {temp_dir} [GITOPS-PARTIAL22]')
                except Exception as cleanup_err:
                    logger.error(f'Failed to cleanup temp directory {temp_dir}: {str(cleanup_err)} [GITOPS-PARTIAL23]')

    def copy_folder_to_static(self, folder_path: str, branch_name: str = 'main') -> Dict:
        """
        Lightweight copy of folder with .gitkeep to static directory.
        Used for folder creation to avoid full rebuild overhead.

        Args:
            folder_path: Path to folder (e.g., 'docs/guides')
            branch_name: Branch to copy from (default: 'main')

        Returns:
            Dict with success status

        Raises:
            GitRepositoryError: If copy fails
        """
        try:
            logger.info(f'Copying folder {folder_path} to static directory [GITOPS-FOLDER01]')

            # Source and destination paths
            source_folder = self.repo_path / folder_path
            static_folder = settings.WIKI_STATIC_PATH / branch_name / folder_path

            if not source_folder.exists():
                raise GitRepositoryError(f"Folder {folder_path} does not exist in repository")

            # Create static folder
            static_folder.mkdir(parents=True, exist_ok=True)

            # Copy .gitkeep file
            gitkeep_source = source_folder / '.gitkeep'
            if gitkeep_source.exists():
                gitkeep_dest = static_folder / '.gitkeep'
                shutil.copy2(gitkeep_source, gitkeep_dest)
                logger.info(f'Copied .gitkeep to {static_folder} [GITOPS-FOLDER02]')

            # Invalidate parent directory cache
            from config.cache_utils import invalidate_file_cache
            from django.core.cache import cache

            parent_path = str(Path(folder_path).parent)
            if parent_path == '.':
                parent_path = ''

            # Invalidate parent directory listing
            cache_key = f'directory:{branch_name}:{parent_path}'
            cache.delete(cache_key)
            logger.info(f'Invalidated cache for parent directory {parent_path} [GITOPS-FOLDER03]')

            return {
                'success': True,
                'folder_path': folder_path,
                'branch_name': branch_name
            }

        except Exception as e:
            error_msg = f'Failed to copy folder to static: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-FOLDER04]')
            raise GitRepositoryError(error_msg)

    def get_conflicts(self, cache_timeout: int = 120) -> Dict:
        """
        Get list of all draft branches with merge conflicts.

        AIDEV-NOTE: conflict-detection; Caches results for 2min to avoid expensive operations

        Args:
            cache_timeout: Cache timeout in seconds (default: 120 = 2 minutes)

        Returns:
            Dict with conflicts list, cache status, and timestamp:
            {
                "conflicts": [
                    {
                        "branch_name": "draft-123-abc456",
                        "file_paths": ["docs/page.md"],
                        "user_id": 123,
                        "created_at": "2025-10-25T10:00:00Z"
                    }
                ],
                "cached": false,
                "timestamp": "2025-10-25T10:00:00Z"
            }
        """
        from django.core.cache import cache

        start_time = time.time()
        cache_key = 'git_conflicts_list'

        try:
            # Check cache first
            cached = cache.get(cache_key)
            if cached:
                logger.info('Returning cached conflicts list [GITOPS-CONFLICT03]')
                cached['cached'] = True
                return cached

            logger.info('Detecting conflicts (cache miss) [GITOPS-CONFLICT04]')

            # Get all draft branches
            draft_branches = self.list_branches(pattern='draft-*')

            conflicts = []

            # Check each draft branch for conflicts
            for branch_name in draft_branches:
                try:
                    has_conflict, conflicted_files = self._check_merge_conflicts(branch_name)

                    if has_conflict and conflicted_files:
                        # Extract user_id from branch name (draft-{user_id}-{uuid})
                        parts = branch_name.split('-')
                        user_id = int(parts[1]) if len(parts) >= 2 else None

                        # Get branch creation time
                        try:
                            branch = self.repo.heads[branch_name]
                            created_at = datetime.fromtimestamp(branch.commit.committed_date).isoformat()
                        except Exception:
                            created_at = datetime.now().isoformat()

                        conflicts.append({
                            'branch_name': branch_name,
                            'file_paths': conflicted_files,
                            'user_id': user_id,
                            'created_at': created_at
                        })

                except Exception as e:
                    logger.warning(f'Failed to check conflicts for {branch_name}: {str(e)} [GITOPS-CONFLICT05]')
                    continue

            result = {
                'conflicts': conflicts,
                'cached': False,
                'timestamp': datetime.now().isoformat()
            }

            # Cache the result
            cache.set(cache_key, result, cache_timeout)

            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f'Found {len(conflicts)} conflicts in {execution_time}ms [GITOPS-CONFLICT02]')

            return result

        except Exception as e:
            error_msg = f'Failed to get conflicts: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-CONFLICT06]')
            raise GitRepositoryError(error_msg)

    def get_conflict_versions(self, branch_name: str, file_path: str) -> Dict[str, str]:
        """
        Extract three versions for conflict resolution (base, theirs, ours).

        AIDEV-NOTE: three-way-diff; Extracts base, theirs, ours for Monaco Editor

        Args:
            branch_name: Draft branch name
            file_path: Path to conflicted file

        Returns:
            Dict with three versions:
            {
                "base": "content from common ancestor",
                "theirs": "content from main branch",
                "ours": "content from draft branch"
            }
        """
        try:
            # Validate branch exists
            if not self._has_branch(branch_name):
                raise GitRepositoryError(f"Branch {branch_name} does not exist")

            # Get merge base (common ancestor)
            main_commit = self.repo.heads.main.commit
            draft_commit = self.repo.heads[branch_name].commit
            merge_bases = self.repo.merge_base(main_commit, draft_commit)

            if not merge_bases:
                logger.warning(f'No merge base found for {branch_name} and main [GITOPS-CONFLICT07]')
                base_content = ""
            else:
                base_commit = merge_bases[0]
                try:
                    base_content = base_commit.tree[file_path].data_stream.read().decode('utf-8')
                except KeyError:
                    # File didn't exist in base
                    base_content = ""

            # Get content from main branch (theirs)
            try:
                theirs_content = main_commit.tree[file_path].data_stream.read().decode('utf-8')
            except KeyError:
                theirs_content = ""

            # Get content from draft branch (ours)
            try:
                ours_content = draft_commit.tree[file_path].data_stream.read().decode('utf-8')
            except KeyError:
                ours_content = ""

            logger.info(f'Extracted conflict versions for {file_path} in {branch_name} [GITOPS-CONFLICT08]')

            return {
                'base': base_content,
                'theirs': theirs_content,
                'ours': ours_content,
                'file_path': file_path,
                'branch_name': branch_name
            }

        except Exception as e:
            error_msg = f'Failed to get conflict versions: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-CONFLICT09]')
            raise GitRepositoryError(error_msg)

    def resolve_conflict(
        self,
        branch_name: str,
        file_path: str,
        resolution_content: str,
        user_info: Dict,
        is_binary: bool = False
    ) -> Dict:
        """
        Apply conflict resolution and retry merge.

        AIDEV-NOTE: conflict-resolution; Retries merge after applying resolution

        Args:
            branch_name: Draft branch name
            file_path: Path to conflicted file
            resolution_content: Resolved content (or file path for binary)
            user_info: User information dict with 'name' and 'email'
            is_binary: Whether this is a binary file

        Returns:
            Dict with resolution status:
            {
                "success": true,
                "merged": true,
                "commit_hash": "abc123...",
                "still_conflicts": []  # if merge still failed
            }
        """
        start_time = time.time()

        try:
            # Validate branch exists
            if not self._has_branch(branch_name):
                raise GitRepositoryError(f"Branch {branch_name} does not exist")

            # Save current branch
            current_branch = self.repo.active_branch.name

            # Checkout draft branch
            self.repo.heads[branch_name].checkout()

            # Write resolved content
            file_full_path = self.repo_path / file_path

            if not is_binary:
                # Text file - write content
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                file_full_path.write_text(resolution_content, encoding='utf-8')
            else:
                # Binary file - resolution_content is the source path
                if not Path(resolution_content).exists():
                    raise GitRepositoryError(f"Binary file not found: {resolution_content}")
                shutil.copy2(resolution_content, file_full_path)

            # Stage the resolved file
            self.repo.index.add([file_path])

            # Commit the resolution
            commit_message = f"Resolve conflict in {file_path}"
            self.repo.index.commit(
                commit_message,
                author=git.Actor(user_info.get('name', 'Unknown'), user_info.get('email', 'unknown@example.com'))
            )

            resolution_commit = self.repo.head.commit.hexsha

            logger.info(f'Applied conflict resolution for {file_path} in {branch_name} [GITOPS-RESOLVE01]')

            # Now try to publish again
            try:
                result = self.publish_draft(branch_name, user=None, auto_push=True)

                if result['success']:
                    execution_time = int((time.time() - start_time) * 1000)

                    GitOperation.log_operation(
                        operation_type='conflict_resolution',
                        branch_name=branch_name,
                        file_path=file_path,
                        request_params={
                            'file_path': file_path,
                            'is_binary': is_binary
                        },
                        response_code=200,
                        success=True,
                        git_output=f'Resolved and merged {file_path}',
                        execution_time_ms=execution_time
                    )

                    logger.info(f'Conflict resolved and merged successfully [GITOPS-RESOLVE02]')

                    return {
                        'success': True,
                        'merged': True,
                        'commit_hash': result.get('commit_hash', resolution_commit),
                        'still_conflicts': []
                    }
                else:
                    # Still has conflicts
                    logger.warning(f'Conflict resolution incomplete, still has conflicts [GITOPS-RESOLVE03]')

                    return {
                        'success': True,
                        'merged': False,
                        'commit_hash': resolution_commit,
                        'still_conflicts': result.get('conflicts', [])
                    }

            except Exception as e:
                logger.error(f'Failed to merge after resolution: {str(e)} [GITOPS-RESOLVE04]')

                return {
                    'success': True,
                    'merged': False,
                    'commit_hash': resolution_commit,
                    'still_conflicts': [{'file_path': file_path, 'error': str(e)}]
                }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f'Failed to resolve conflict: {str(e)}'

            GitOperation.log_operation(
                operation_type='conflict_resolution',
                branch_name=branch_name,
                file_path=file_path,
                request_params={
                    'file_path': file_path,
                    'is_binary': is_binary
                },
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time
            )

            logger.error(f'{error_msg} [GITOPS-RESOLVE05]')
            raise GitRepositoryError(error_msg)

    def pull_from_github(self) -> Dict:
        """
        Pull latest changes from GitHub remote repository.

        AIDEV-NOTE: github-pull; Handles conflicts during pull gracefully

        Process:
        1. Git fetch from remote
        2. Check for diverged branches
        3. Git pull (merge remote changes)
        4. Detect changed files
        5. Trigger static regeneration if needed
        6. Log operation

        Returns:
            {
                "success": true,
                "changes_detected": true,
                "files_changed": ["docs/page1.md", "docs/page2.md"],
                "static_regenerated": true,
                "conflicts": []
            }

        Error Codes:
            401: SSH authentication failed
            502: GitHub connection failed
            409: Merge conflicts during pull
            500: Git operation failed
        """
        from django.core.cache import cache

        start_time = time.time()

        try:
            # Get GitHub remote URL from configuration
            remote_url = Configuration.get_config('github_remote_url')
            if not remote_url:
                error_msg = 'GitHub remote URL not configured'
                logger.warning(f'{error_msg} [GITOPS-PULL01]')
                return {
                    'success': False,
                    'message': error_msg,
                    'changes_detected': False
                }

            logger.info(f'Pulling from GitHub: {remote_url} [GITOPS-PULL02]')

            # Ensure we're on main branch
            if self.repo.active_branch.name != 'main':
                self.repo.heads.main.checkout()

            # Get current HEAD for comparison
            old_commit = self.repo.head.commit.hexsha

            # Fetch from remote
            try:
                origin = self.repo.remote('origin')
            except ValueError:
                # Remote doesn't exist, add it
                origin = self.repo.create_remote('origin', remote_url)
                logger.info(f'Created remote origin: {remote_url} [GITOPS-PULL03]')

            # Fetch latest changes
            fetch_info = origin.fetch()

            # Pull changes (merge)
            try:
                pull_info = origin.pull('main')

                # Get new HEAD
                new_commit = self.repo.head.commit.hexsha

                # Detect changed files
                changed_files = []
                if old_commit != new_commit:
                    diff = self.repo.git.diff(old_commit, new_commit, name_only=True)
                    changed_files = [f for f in diff.split('\n') if f]

                    logger.info(f'Pulled {len(changed_files)} changed files from GitHub [GITOPS-PULL04]')

                    # Trigger static regeneration if markdown files changed
                    md_files_changed = [f for f in changed_files if f.endswith('.md')]
                    static_regenerated = False

                    if md_files_changed:
                        try:
                            self.write_branch_to_disk('main')
                            static_regenerated = True
                            logger.info('Static files regenerated after pull [GITOPS-PULL05]')
                        except Exception as e:
                            logger.warning(f'Static regeneration failed after pull: {str(e)} [GITOPS-PULL06]')

                    # Update cache with last pull time
                    cache.set('last_github_pull_time', datetime.now().isoformat(), None)

                    execution_time = int((time.time() - start_time) * 1000)

                    GitOperation.log_operation(
                        operation_type='github_pull',
                        branch_name='main',
                        request_params={'remote_url': remote_url},
                        response_code=200,
                        success=True,
                        git_output=f'Pulled {len(changed_files)} files',
                        execution_time_ms=execution_time
                    )

                    return {
                        'success': True,
                        'changes_detected': True,
                        'files_changed': changed_files,
                        'static_regenerated': static_regenerated,
                        'commits_pulled': len(list(self.repo.iter_commits(f'{old_commit}..{new_commit}')))
                    }
                else:
                    logger.info('No changes detected in GitHub pull [GITOPS-PULL07]')
                    return {
                        'success': True,
                        'changes_detected': False,
                        'files_changed': [],
                        'static_regenerated': False
                    }

            except git.exc.GitCommandError as e:
                # Check for merge conflicts
                if 'CONFLICT' in str(e):
                    error_msg = 'Merge conflicts detected during pull'
                    logger.warning(f'{error_msg} [GITOPS-PULL08]')

                    # Abort the merge
                    self.repo.git.merge('--abort')

                    GitOperation.log_operation(
                        operation_type='github_pull',
                        branch_name='main',
                        request_params={'remote_url': remote_url},
                        response_code=409,
                        success=False,
                        error_message=error_msg,
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )

                    return {
                        'success': False,
                        'message': error_msg,
                        'changes_detected': False,
                        'conflicts': True
                    }
                else:
                    raise

        except git.exc.GitCommandError as e:
            error_msg = f'Git command error during pull: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-PULL09]')

            GitOperation.log_operation(
                operation_type='github_pull',
                branch_name='main',
                request_params={'remote_url': remote_url if 'remote_url' in locals() else None},
                response_code=502,
                success=False,
                error_message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

            return {
                'success': False,
                'message': error_msg,
                'changes_detected': False
            }

        except Exception as e:
            error_msg = f'Failed to pull from GitHub: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-PULL10]')

            GitOperation.log_operation(
                operation_type='github_pull',
                branch_name='main',
                request_params={'remote_url': remote_url if 'remote_url' in locals() else None},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

            raise GitRepositoryError(error_msg)

    def push_to_github(self, branch: str = "main") -> Dict:
        """
        Push local changes to GitHub remote repository.

        AIDEV-NOTE: github-push; Only pushes if local is ahead

        Args:
            branch: Branch name to push (default: main)

        Process:
        1. Check for unpushed commits
        2. Verify SSH connection
        3. Git push to remote
        4. Handle push failures
        5. Log operation

        Returns:
            {
                "success": true,
                "branch": "main",
                "commits_pushed": 3,
                "remote_updated": true
            }

        Error Codes:
            409: Remote has changes, need to pull first
            401: SSH authentication failed
            502: GitHub connection failed
            500: Git operation failed
        """
        start_time = time.time()

        try:
            # Get GitHub remote URL from configuration
            remote_url = Configuration.get_config('github_remote_url')
            if not remote_url:
                error_msg = 'GitHub remote URL not configured'
                logger.warning(f'{error_msg} [GITOPS-PUSH01]')
                return {
                    'success': False,
                    'message': error_msg,
                    'commits_pushed': 0
                }

            logger.info(f'Pushing to GitHub: {remote_url} [GITOPS-PUSH02]')

            # Ensure branch exists
            if not self._has_branch(branch):
                error_msg = f'Branch {branch} does not exist'
                logger.error(f'{error_msg} [GITOPS-PUSH03]')
                raise GitRepositoryError(error_msg)

            # Checkout target branch
            if self.repo.active_branch.name != branch:
                self.repo.heads[branch].checkout()

            # Get remote
            try:
                origin = self.repo.remote('origin')
            except ValueError:
                # Remote doesn't exist, add it
                origin = self.repo.create_remote('origin', remote_url)
                logger.info(f'Created remote origin: {remote_url} [GITOPS-PUSH04]')

            # Fetch to check if remote has changes
            try:
                origin.fetch()

                # Check if local is ahead, behind, or diverged
                try:
                    # Count commits ahead
                    commits_ahead = list(self.repo.iter_commits(f'origin/{branch}..{branch}'))
                    commits_behind = list(self.repo.iter_commits(f'{branch}..origin/{branch}'))

                    if commits_behind:
                        error_msg = f'Remote has {len(commits_behind)} commits you don\'t have. Pull first.'
                        logger.warning(f'{error_msg} [GITOPS-PUSH05]')

                        GitOperation.log_operation(
                            operation_type='github_push',
                            branch_name=branch,
                            request_params={'remote_url': remote_url},
                            response_code=409,
                            success=False,
                            error_message=error_msg,
                            execution_time_ms=int((time.time() - start_time) * 1000)
                        )

                        return {
                            'success': False,
                            'message': error_msg,
                            'commits_pushed': 0,
                            'commits_behind': len(commits_behind)
                        }

                    if not commits_ahead:
                        logger.info('No commits to push [GITOPS-PUSH06]')
                        return {
                            'success': True,
                            'message': 'No commits to push',
                            'commits_pushed': 0,
                            'commits_behind': 0
                        }

                except git.exc.GitCommandError:
                    # Remote branch doesn't exist yet (first push)
                    commits_ahead = list(self.repo.iter_commits(branch))
                    logger.info(f'First push to new remote branch {branch} [GITOPS-PUSH07]')

            except git.exc.GitCommandError as e:
                logger.warning(f'Could not fetch remote: {str(e)} [GITOPS-PUSH08]')
                commits_ahead = list(self.repo.iter_commits(branch))

            # Push to remote
            try:
                push_info = origin.push(branch)

                execution_time = int((time.time() - start_time) * 1000)

                logger.info(f'Pushed {len(commits_ahead)} commits to GitHub [GITOPS-PUSH09]')

                GitOperation.log_operation(
                    operation_type='github_push',
                    branch_name=branch,
                    request_params={'remote_url': remote_url},
                    response_code=200,
                    success=True,
                    git_output=f'Pushed {len(commits_ahead)} commits',
                    execution_time_ms=execution_time
                )

                return {
                    'success': True,
                    'branch': branch,
                    'commits_pushed': len(commits_ahead),
                    'remote_updated': True
                }

            except git.exc.GitCommandError as e:
                error_msg = f'Git push failed: {str(e)}'
                logger.error(f'{error_msg} [GITOPS-PUSH10]')

                # Check for specific errors
                if 'rejected' in str(e).lower():
                    response_code = 409
                    error_msg = 'Push rejected - remote has changes. Pull first.'
                elif 'permission denied' in str(e).lower() or 'authentication failed' in str(e).lower():
                    response_code = 401
                    error_msg = 'SSH authentication failed - check your SSH key'
                else:
                    response_code = 502

                GitOperation.log_operation(
                    operation_type='github_push',
                    branch_name=branch,
                    request_params={'remote_url': remote_url},
                    response_code=response_code,
                    success=False,
                    error_message=error_msg,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

                return {
                    'success': False,
                    'message': error_msg,
                    'commits_pushed': 0
                }

        except Exception as e:
            error_msg = f'Failed to push to GitHub: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-PUSH11]')

            GitOperation.log_operation(
                operation_type='github_push',
                branch_name=branch,
                request_params={'remote_url': remote_url if 'remote_url' in locals() else None},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

            raise GitRepositoryError(error_msg)

    def cleanup_stale_branches(self, age_days: int = 7) -> Dict:
        """
        Remove old draft branches and their static files.

        AIDEV-NOTE: branch-cleanup; Only removes inactive sessions

        Args:
            age_days: Remove branches older than this (default: 7 days)

        Process:
        1. List all draft branches
        2. Check last commit date
        3. Check if EditSession is still active
        4. Delete old, inactive branches
        5. Remove associated static files
        6. Log operation

        Returns:
            {
                "success": true,
                "branches_deleted": ["draft-123-abc", "draft-456-def"],
                "branches_kept": ["draft-789-ghi"],
                "disk_space_freed_mb": 150
            }
        """
        from editor.models import EditSession

        start_time = time.time()
        cutoff_date = datetime.now() - timedelta(days=age_days)

        try:
            logger.info(f'Starting branch cleanup (age_days={age_days}) [GITOPS-CLEANUP01]')

            # Get all draft branches
            draft_branches = self.list_branches(pattern='draft-*')

            branches_deleted = []
            branches_kept = []
            disk_space_freed = 0

            for branch_name in draft_branches:
                try:
                    # Get branch object
                    branch = self.repo.heads[branch_name]

                    # Get last commit date
                    last_commit_date = datetime.fromtimestamp(branch.commit.committed_date)

                    # Check if branch is old enough
                    if last_commit_date > cutoff_date:
                        branches_kept.append(branch_name)
                        logger.debug(f'Keeping recent branch {branch_name} [GITOPS-CLEANUP02]')
                        continue

                    # Check if associated EditSession is still active
                    active_session = EditSession.objects.filter(
                        branch_name=branch_name,
                        is_active=True
                    ).exists()

                    if active_session:
                        branches_kept.append(branch_name)
                        logger.info(f'Keeping branch {branch_name} (active session) [GITOPS-CLEANUP03]')
                        continue

                    # Calculate disk space of static files
                    static_path = settings.WIKI_STATIC_PATH / branch_name
                    if static_path.exists():
                        branch_size = sum(f.stat().st_size for f in static_path.rglob('*') if f.is_file())
                        disk_space_freed += branch_size

                        # Remove static files
                        shutil.rmtree(static_path)
                        logger.info(f'Removed static files for {branch_name} [GITOPS-CLEANUP04]')

                    # Delete the branch
                    self.repo.delete_head(branch_name, force=True)
                    branches_deleted.append(branch_name)

                    # Mark EditSession as inactive
                    EditSession.objects.filter(branch_name=branch_name).update(is_active=False)

                    logger.info(f'Deleted stale branch {branch_name} [GITOPS-CLEANUP05]')

                except Exception as e:
                    logger.warning(f'Failed to delete branch {branch_name}: {str(e)} [GITOPS-CLEANUP06]')
                    branches_kept.append(branch_name)
                    continue

            execution_time = int((time.time() - start_time) * 1000)
            disk_space_freed_mb = disk_space_freed / (1024 * 1024)

            logger.info(
                f'Branch cleanup complete: {len(branches_deleted)} deleted, '
                f'{len(branches_kept)} kept, {disk_space_freed_mb:.2f}MB freed [GITOPS-CLEANUP07]'
            )

            GitOperation.log_operation(
                operation_type='cleanup_branches',
                request_params={'age_days': age_days},
                response_code=200,
                success=True,
                git_output=f'Deleted {len(branches_deleted)} branches',
                execution_time_ms=execution_time
            )

            return {
                'success': True,
                'branches_deleted': branches_deleted,
                'branches_kept': branches_kept,
                'disk_space_freed_mb': round(disk_space_freed_mb, 2)
            }

        except Exception as e:
            error_msg = f'Failed to cleanup stale branches: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-CLEANUP08]')

            GitOperation.log_operation(
                operation_type='cleanup_branches',
                request_params={'age_days': age_days},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

            raise GitRepositoryError(error_msg)

    def full_static_rebuild(self) -> Dict:
        """
        Complete regeneration of all static files.

        AIDEV-NOTE: static-rebuild; Atomic operation, old files kept until complete

        Process:
        1. Generate to temp directory
        2. Regenerate main branch
        3. Regenerate active draft branches
        4. Verify integrity
        5. Atomic swap
        6. Log operation

        Returns:
            {
                "success": true,
                "branches_regenerated": ["main", "draft-123-abc"],
                "total_files": 150,
                "execution_time_ms": 5000
            }
        """
        from editor.models import EditSession

        start_time = time.time()

        try:
            logger.info('Starting full static rebuild [GITOPS-REBUILD01]')

            branches_regenerated = []
            total_files = 0

            # Regenerate main branch
            try:
                result = self.write_branch_to_disk('main')
                branches_regenerated.append('main')
                # Count markdown files in main branch
                for root, dirs, files in os.walk(self.repo_path):
                    total_files += len([f for f in files if f.endswith('.md')])
                logger.info('Main branch static files regenerated [GITOPS-REBUILD02]')
            except Exception as e:
                logger.error(f'Failed to regenerate main branch: {str(e)} [GITOPS-REBUILD03]')
                raise

            # Get active draft branches
            active_sessions = EditSession.objects.filter(is_active=True).values_list('branch_name', flat=True)
            active_branches = list(set(active_sessions))  # Remove duplicates

            # Regenerate active draft branches
            for branch_name in active_branches:
                try:
                    if self._has_branch(branch_name):
                        result = self.write_branch_to_disk(branch_name)
                        branches_regenerated.append(branch_name)
                        logger.info(f'Regenerated static files for {branch_name} [GITOPS-REBUILD04]')
                except Exception as e:
                    logger.warning(f'Failed to regenerate {branch_name}: {str(e)} [GITOPS-REBUILD05]')
                    continue

            # Clean up old static directories not in branches_regenerated
            static_root = settings.WIKI_STATIC_PATH
            if static_root.exists():
                for item in static_root.iterdir():
                    if item.is_dir() and item.name not in branches_regenerated:
                        # Check if it's a draft branch that no longer exists
                        if item.name.startswith('draft-'):
                            try:
                                shutil.rmtree(item)
                                logger.info(f'Removed orphaned static dir: {item.name} [GITOPS-REBUILD06]')
                            except Exception as e:
                                logger.warning(f'Failed to remove {item.name}: {str(e)} [GITOPS-REBUILD07]')

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(
                f'Full static rebuild complete: {len(branches_regenerated)} branches, '
                f'{total_files} files, {execution_time}ms [GITOPS-REBUILD08]'
            )

            # Clear all caches after full rebuild
            from config.cache_utils import clear_all_caches
            cache_result = clear_all_caches()
            if cache_result['success']:
                logger.info('Caches cleared after full static rebuild [GITOPS-REBUILD10]')
            else:
                logger.warning(f'Cache clear failed: {cache_result["message"]} [GITOPS-REBUILD11]')

            GitOperation.log_operation(
                operation_type='static_rebuild',
                request_params={},
                response_code=200,
                success=True,
                git_output=f'Regenerated {len(branches_regenerated)} branches',
                execution_time_ms=execution_time
            )

            return {
                'success': True,
                'branches_regenerated': branches_regenerated,
                'total_files': total_files,
                'execution_time_ms': execution_time,
                'caches_cleared': cache_result['success']
            }

        except Exception as e:
            error_msg = f'Failed to rebuild static files: {str(e)}'
            logger.error(f'{error_msg} [GITOPS-REBUILD09]')

            GitOperation.log_operation(
                operation_type='static_rebuild',
                request_params={},
                response_code=500,
                success=False,
                error_message=error_msg,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

            raise GitRepositoryError(error_msg)


# Global repository instance
# AIDEV-NOTE: thread-safe-singleton; Lock protects initialization from race conditions
_repo_instance = None
_repo_lock = threading.Lock()


def get_repository() -> GitRepository:
    """
    Get global GitRepository instance (singleton pattern).

    Thread-safe implementation using double-checked locking pattern.
    This prevents race conditions when multiple threads try to initialize
    the repository simultaneously in multi-threaded environments like
    Gunicorn with threading workers.

    Returns:
        GitRepository instance
    """
    global _repo_instance

    # First check (without lock) for performance
    if _repo_instance is None:
        # Acquire lock for initialization
        with _repo_lock:
            # Second check (with lock) to prevent race condition
            if _repo_instance is None:
                _repo_instance = GitRepository()

    return _repo_instance
