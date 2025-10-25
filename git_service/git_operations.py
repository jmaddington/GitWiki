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

            # Checkout branch
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

            # Trigger static file generation for main branch
            try:
                self.write_branch_to_disk('main', user)
                logger.info(f'Generated static files after merge [GITOPS-PUBLISH04]')
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
        Convert markdown to HTML with table of contents.

        Args:
            content: Markdown content

        Returns:
            Tuple of (html_content, toc_html)

        AIDEV-NOTE: markdown-conversion; Uses markdown library with extensions for tables, code, TOC
        """
        try:
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

            return html_content, toc_html

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

            # Copy all files from repository
            for item in self.repo_path.rglob('*'):
                if item.is_file() and '.git' not in str(item):
                    rel_path = item.relative_to(self.repo_path)
                    dest_path = temp_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, dest_path)
                    files_written += 1

                    # Track markdown files for HTML generation
                    if item.suffix == '.md':
                        markdown_files.append(str(rel_path))

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
                shutil.rmtree(final_dir)
            shutil.move(str(temp_dir), str(final_dir))

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
            # Cleanup temp directory on error
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir)

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
