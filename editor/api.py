"""
API views for Editor Service.

AIDEV-NOTE: editor-api; REST API for markdown editing workflow with standardized error handling
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from pathlib import Path
import logging
import markdown
import os
import uuid
import tempfile
from datetime import datetime

from .models import EditSession
from .serializers import (
    StartEditSerializer,
    SaveDraftSerializer,
    CommitDraftSerializer,
    PublishEditSerializer,
    ResolveConflictSerializer,
    ValidateMarkdownSerializer,
    UploadImageSerializer,
    UploadFileSerializer,
    QuickUploadFileSerializer,
    DeleteFileSerializer,
    DiscardDraftSerializer
)
from git_service.git_operations import get_repository, GitRepositoryError
from git_service.models import Configuration
from config.api_utils import (
    error_response,
    success_response,
    validation_error_response,
    handle_exception,
    get_user_info_for_commit
)

logger = logging.getLogger(__name__)


def _ensure_branch_exists(session: 'EditSession', repo) -> bool:
    """
    Ensure the session's branch exists, recreating it if necessary.

    Args:
        session: The EditSession to check
        repo: GitRepository instance

    Returns:
        True if branch exists or was recreated, False on error

    Note:
        Logs warnings if branch needs to be recreated.
    """
    if repo._has_branch(session.branch_name):
        return True

    logger.warning(
        f'Branch {session.branch_name} missing for session {session.id}, recreating [EDITOR-BRANCH-RECREATE01]'
    )

    try:
        # Recreate the branch from main
        # Extract user_id from branch name (draft-{user_id}-{uuid})
        parts = session.branch_name.split('-')
        user_id = int(parts[1]) if len(parts) >= 2 else session.user.id

        # Create new branch with same name
        repo.repo.heads.main.checkout()
        new_branch = repo.repo.create_head(session.branch_name)
        new_branch.checkout()

        logger.info(f'Recreated branch {session.branch_name} for session {session.id} [EDITOR-BRANCH-RECREATE02]')
        return True

    except Exception as e:
        logger.error(f'Failed to recreate branch {session.branch_name}: {e} [EDITOR-BRANCH-RECREATE03]', exc_info=True)
        return False


class StartEditAPIView(APIView):
    """
    API endpoint to start editing a file.

    POST /api/editor/start/
    {
        "file_path": "docs/getting-started.md"
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Start an edit session with atomic transaction support."""
        # Validate input
        serializer = StartEditSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-START-VAL01")

        data = serializer.validated_data
        file_path = data['file_path']

        try:
            # Get authenticated user
            user = request.user

            # Check if user already has an active session for this file
            existing_session = EditSession.get_user_session_for_file(user, file_path)
            if existing_session:
                repo = get_repository()

                # Check if the branch still exists
                if not repo._has_branch(existing_session.branch_name):
                    logger.warning(
                        f'Session {existing_session.id} branch {existing_session.branch_name} no longer exists, '
                        f'creating new session [EDITOR-START-STALE01]'
                    )
                    # Mark old session as inactive
                    existing_session.mark_inactive()
                    # Fall through to create new session
                else:
                    # Resume existing session
                    logger.info(f'Resuming existing edit session: {existing_session.id} [EDITOR-START01]')

                    # Get current content from branch
                    try:
                        content = repo.get_file_content(file_path, existing_session.branch_name)
                    except GitRepositoryError:
                        # File doesn't exist in branch yet, get from main
                        try:
                            content = repo.get_file_content(file_path, 'main')
                        except GitRepositoryError:
                            # File doesn't exist anywhere, start with empty content
                            content = f"# {Path(file_path).stem.replace('-', ' ').title()}\n\n"

                    # AIDEV-NOTE: draft-staleness-check; Detect if draft differs from main
                    is_stale = False
                    main_content = None
                    try:
                        main_content = repo.get_file_content(file_path, 'main')
                        is_stale = (content != main_content)
                    except GitRepositoryError:
                        # File doesn't exist in main, so not stale
                        pass

                    return success_response(
                        data={
                            'session_id': existing_session.id,
                            'branch_name': existing_session.branch_name,
                            'file_path': file_path,
                            'content': content,
                            'created_at': existing_session.created_at,
                            'last_modified': existing_session.last_modified,
                            'resumed': True,
                            'is_stale': is_stale
                        },
                        message=f"Resumed edit session for '{file_path}'"
                    )

            # Create new draft branch
            repo = get_repository()
            branch_result = repo.create_draft_branch(user.id, user=user)

            # Create edit session with race condition handling (fixes #22)
            # AIDEV-NOTE: race-condition-handling; Handle concurrent session creation attempts
            try:
                session = EditSession.objects.create(
                    user=user,
                    file_path=file_path,
                    branch_name=branch_result['branch_name']
                )
            except IntegrityError as e:
                # Constraint violation - session was created by concurrent request
                logger.warning(
                    f'Duplicate session prevented by constraint for user {user.id}:{file_path}, '
                    f'resuming existing session [EDITOR-START-RACE01]'
                )
                # Fetch the session that was just created by the concurrent request
                existing_session = EditSession.get_user_session_for_file(user, file_path)
                if existing_session:
                    # Resume the existing session
                    try:
                        content = repo.get_file_content(file_path, existing_session.branch_name)
                    except GitRepositoryError:
                        try:
                            content = repo.get_file_content(file_path, 'main')
                        except GitRepositoryError:
                            content = f"# {Path(file_path).stem.replace('-', ' ').title()}\n\n"

                    return success_response(
                        data={
                            'session_id': existing_session.id,
                            'branch_name': existing_session.branch_name,
                            'file_path': file_path,
                            'content': content,
                            'created_at': existing_session.created_at,
                            'last_modified': existing_session.last_modified,
                            'resumed': True
                        },
                        message=f"Resumed existing session created by concurrent request for '{file_path}'"
                    )
                # If still no session found, re-raise the error
                logger.error(f'Failed to find session after IntegrityError [EDITOR-START-RACE02]', exc_info=True)
                raise

            # Get file content from main branch, or create new
            try:
                content = repo.get_file_content(file_path, 'main')
            except GitRepositoryError:
                # File doesn't exist, create template
                content = f"# {Path(file_path).stem.replace('-', ' ').title()}\n\n"

            logger.info(f'Started new edit session: {session.id} for {file_path} [EDITOR-START02]')

            return success_response(
                data={
                    'session_id': session.id,
                    'branch_name': branch_result['branch_name'],
                    'file_path': file_path,
                    'content': content,
                    'created_at': session.created_at,
                    'last_modified': session.last_modified,
                    'resumed': False
                },
                message=f"Started new edit session for '{file_path}'",
                status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            response, should_rollback = handle_exception(
                e, "start edit session", "EDITOR-START03",
                f"Failed to start edit session for '{file_path}'. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class SaveDraftAPIView(APIView):
    """
    API endpoint to save draft (validate and update timestamp).

    POST /api/editor/save/
    {
        "session_id": 456,
        "content": "# Page Title\nContent..."
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Save draft with validation and atomic transaction support."""
        # Validate input
        serializer = SaveDraftSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-SAVE-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']
        content = data['content']

        try:
            # Get edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)

            # Validate markdown
            validation = self._validate_markdown(content)

            # Update session timestamp
            session.touch()

            logger.info(f'Draft saved for session {session_id} [EDITOR-SAVE01]')

            return success_response(
                data={
                    'saved_at': session.last_modified,
                    'markdown_valid': validation['valid'],
                    'validation_errors': validation.get('errors', []),
                    'validation_warnings': validation.get('warnings', [])
                },
                message="Draft saved successfully"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-SAVE02]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or inactive",
                error_code="EDITOR-SAVE-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "save draft", "EDITOR-SAVE03",
                "Failed to save draft. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response

    def _validate_markdown(self, content):
        """Validate markdown syntax."""
        try:
            # Parse markdown
            html = markdown.markdown(content, extensions=['extra', 'codehilite'])

            # Basic validation - check for common issues
            warnings = []

            # Check for unclosed code blocks
            if content.count('```') % 2 != 0:
                warnings.append({'line': None, 'message': 'Unclosed code block detected', 'severity': 'warning'})

            return {
                'valid': True,
                'warnings': warnings
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [{'message': str(e), 'severity': 'error'}]
            }


class CommitDraftAPIView(APIView):
    """
    API endpoint to commit draft to Git branch.

    POST /api/editor/commit/
    {
        "session_id": 456,
        "content": "# Page Title\nContent...",
        "commit_message": "Update page content"
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Commit draft to Git branch with atomic transaction support."""
        # Validate input
        serializer = CommitDraftSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-COMMIT-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']
        content = data['content']
        commit_message = data['commit_message']

        try:
            # Get edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)

            # Validate markdown (hard error on invalid)
            save_view = SaveDraftAPIView()
            validation = save_view._validate_markdown(content)

            if not validation['valid']:
                return error_response(
                    message="Invalid markdown syntax. Please fix errors before committing.",
                    error_code="EDITOR-COMMIT-INVALID",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    details={'validation_errors': validation.get('errors', [])}
                )

            # Ensure branch exists (recreate if missing)
            repo = get_repository()
            if not _ensure_branch_exists(session, repo):
                return error_response(
                    message="Failed to recreate missing branch. Please start a new edit session.",
                    error_code="EDITOR-COMMIT-BRANCH-MISSING",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    details={'session_id': session_id, 'branch_name': session.branch_name}
                )

            # Commit to Git
            commit_result = repo.commit_changes(
                branch_name=session.branch_name,
                file_path=session.file_path,
                content=content,
                commit_message=commit_message,
                user_info=get_user_info_for_commit(session.user),
                user=session.user
            )

            # Update session
            session.touch()

            logger.info(f'User {session.user.id} ({session.user.username}) committed draft for session {session_id}: {commit_result["commit_hash"][:8]} [EDITOR-COMMIT01]')

            return success_response(
                data={
                    'commit_hash': commit_result['commit_hash'],
                    'branch_name': session.branch_name
                },
                message=f"Changes committed to {session.file_path}"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-COMMIT02]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or inactive",
                error_code="EDITOR-COMMIT-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "commit draft", "EDITOR-COMMIT03",
                "Failed to commit changes. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class PublishEditAPIView(APIView):
    """
    API endpoint to publish edit to main branch.

    POST /api/editor/publish/
    {
        "session_id": 456,
        "auto_push": true
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Publish edit to main branch with atomic transaction support."""
        # Validate input
        serializer = PublishEditSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-PUBLISH-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']
        content = data.get('content')
        commit_message = data.get('commit_message', 'Update before publish')
        auto_push = data['auto_push']

        try:
            # Get edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)

            repo = get_repository()

            # Ensure branch exists (recreate if missing)
            if not _ensure_branch_exists(session, repo):
                # If we can't even recreate the branch, something is seriously wrong
                session.mark_inactive()
                return error_response(
                    message="Failed to recreate missing branch. Please start a new edit session.",
                    error_code="EDITOR-PUBLISH-BRANCH-MISSING",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    details={'session_id': session_id, 'branch_name': session.branch_name}
                )

            # If content provided, commit it first before publishing
            if content is not None:
                logger.info(f'User {session.user.id} ({session.user.username}) committing content before publish for session {session_id} [EDITOR-PUBLISH-COMMIT01]')
                try:
                    repo.commit_changes(
                        branch_name=session.branch_name,
                        file_path=session.file_path,
                        content=content,
                        commit_message=commit_message,
                        user_info=get_user_info_for_commit(session.user),
                        user=session.user
                    )
                    logger.info(f'Content committed successfully before publish [EDITOR-PUBLISH-COMMIT02]')
                except Exception as commit_error:
                    logger.error(f'Failed to commit content before publish: {commit_error} [EDITOR-PUBLISH-COMMIT03]', exc_info=True)
                    raise

            # Publish to main via Git Service
            publish_result = repo.publish_draft(
                branch_name=session.branch_name,
                user=session.user,
                auto_push=auto_push
            )

            # Check for conflicts
            if not publish_result['success'] and 'conflicts' in publish_result:
                logger.warning(f'User {session.user.id} ({session.user.username}) publish failed due to conflicts: {session.branch_name} [EDITOR-PUBLISH01]')
                return Response({
                    'success': False,
                    'error': {
                        'message': 'Cannot publish due to merge conflicts',
                        'code': 'EDITOR-PUBLISH-CONFLICT',
                        'conflict_details': {
                            'file_path': session.file_path,
                            'conflicts': publish_result['conflicts'],
                            'resolution_url': f'/editor/conflicts/{session.branch_name}'
                        }
                    }
                }, status=status.HTTP_409_CONFLICT)

            # Success - close edit session
            session.mark_inactive()

            logger.info(f'User {session.user.id} ({session.user.username}) published edit session {session_id} to main [EDITOR-PUBLISH02]')

            return success_response(
                data={
                    'published': True,
                    'url': f'/wiki/{session.file_path.replace(".md", "")}'
                },
                message=f"Successfully published '{session.file_path}' to main branch"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-PUBLISH03]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or inactive",
                error_code="EDITOR-PUBLISH-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "publish edit", "EDITOR-PUBLISH04",
                "Failed to publish changes. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class ValidateMarkdownAPIView(APIView):
    """
    API endpoint to validate markdown syntax.

    POST /api/editor/validate/
    {
        "content": "# Page Title\nContent..."
    }
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request):
        """Validate markdown syntax without modifying any data."""
        # Validate input
        serializer = ValidateMarkdownSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-VALIDATE-VAL01")

        content = serializer.validated_data['content']

        # Use the same validation as SaveDraftAPIView
        save_view = SaveDraftAPIView()
        validation = save_view._validate_markdown(content)

        return success_response(
            data=validation,
            message="Markdown validation completed"
        )


class UploadImageAPIView(APIView):
    """
    API endpoint to upload images.

    POST /api/editor/upload-image/
    Form data:
    - session_id: 456
    - image: <file>
    - alt_text: "Screenshot description"
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Upload image with atomic transaction support."""
        # Validate input
        serializer = UploadImageSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-UPLOAD-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']
        image_file = data['image']
        alt_text = data.get('alt_text', '')

        try:
            # Get edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            file_ext = image_file.name.split('.')[-1].lower()
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{Path(session.file_path).stem}-{timestamp}-{unique_id}.{file_ext}"

            # AIDEV-NOTE: image-path-structure; Images stored in images/{branch_name}/
            image_dir = f"images/{session.branch_name}"
            image_path = f"{image_dir}/{filename}"

            # Save image to repository
            repo = get_repository()
            repo_path = repo.repo_path
            full_image_dir = repo_path / image_dir
            full_image_dir.mkdir(parents=True, exist_ok=True)

            # Write image file
            full_image_path = full_image_dir / filename
            with open(full_image_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)

            # Commit image to git
            commit_message = f"Add image: {filename}"
            if alt_text:
                commit_message += f" ({alt_text})"

            repo.commit_changes(
                branch_name=session.branch_name,
                file_path=image_path,
                content='',  # Image is already written to disk
                commit_message=commit_message,
                user_info=get_user_info_for_commit(session.user),
                user=session.user,
                is_binary=True  # Flag to skip content write
            )

            # Generate markdown syntax
            markdown_syntax = f"![{alt_text}]({image_path})"

            logger.info(f'User {session.user.id} ({session.user.username}) uploaded image for session {session_id}: {filename} ({image_file.size} bytes) [EDITOR-UPLOAD01]')

            return success_response(
                data={
                    'filename': filename,
                    'path': image_path,
                    'markdown': markdown_syntax,
                    'file_size_bytes': image_file.size
                },
                message=f"Image '{filename}' uploaded successfully",
                status_code=status.HTTP_201_CREATED
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-UPLOAD02]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or inactive",
                error_code="EDITOR-UPLOAD-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "upload image", "EDITOR-UPLOAD03",
                "Failed to upload image. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class UploadFileAPIView(APIView):
    """
    API endpoint to upload arbitrary files.

    POST /api/editor/upload-file/
    Form data:
    - session_id: 456
    - file: <file>
    - description: "File description"
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Upload arbitrary file with atomic transaction support."""
        # Validate input
        serializer = UploadFileSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-UPLOAD-FILE-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']
        uploaded_file = data['file']
        description = data.get('description', '')

        try:
            # Get edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            file_ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
            unique_id = str(uuid.uuid4())[:8]
            base_name = Path(uploaded_file.name).stem if uploaded_file.name else 'file'
            filename = f"{base_name}-{timestamp}-{unique_id}.{file_ext}" if file_ext else f"{base_name}-{timestamp}-{unique_id}"

            # AIDEV-NOTE: file-path-structure; Arbitrary files stored in files/{branch_name}/
            file_dir = f"files/{session.branch_name}"
            file_path = f"{file_dir}/{filename}"

            # Determine if file is binary
            # AIDEV-NOTE: binary-detection; Text files: .md, .txt, .json, .xml, .html, .css, .js, .py, etc.
            text_extensions = {'md', 'txt', 'json', 'xml', 'html', 'css', 'js', 'py', 'yml', 'yaml', 'toml', 'ini', 'conf', 'log', 'csv', 'tsv'}
            is_binary = file_ext not in text_extensions

            # Save file to repository
            repo = get_repository()
            repo_path = repo.repo_path
            full_file_dir = repo_path / file_dir
            full_file_dir.mkdir(parents=True, exist_ok=True)

            # Write file
            full_file_path = full_file_dir / filename
            with open(full_file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # Commit file to git
            commit_message = f"Add file: {filename}"
            if description:
                commit_message += f" ({description})"

            repo.commit_changes(
                branch_name=session.branch_name,
                file_path=file_path,
                content='',  # File is already written to disk
                commit_message=commit_message,
                user_info=get_user_info_for_commit(session.user),
                user=session.user,
                is_binary=True  # Flag to skip content write
            )

            # Generate markdown link syntax for the file
            markdown_syntax = f"[{uploaded_file.name}]({file_path})"

            logger.info(f'User {session.user.id} ({session.user.username}) uploaded file for session {session_id}: {filename} ({uploaded_file.size} bytes) [EDITOR-UPLOAD-FILE01]')

            return success_response(
                data={
                    'filename': filename,
                    'path': file_path,
                    'markdown': markdown_syntax,
                    'file_size_bytes': uploaded_file.size,
                    'is_binary': is_binary
                },
                message=f"File '{filename}' uploaded successfully",
                status_code=status.HTTP_201_CREATED
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-UPLOAD-FILE02]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or inactive",
                error_code="EDITOR-UPLOAD-FILE-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "upload file", "EDITOR-UPLOAD-FILE03",
                "Failed to upload file. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class QuickUploadFileAPIView(APIView):
    """
    API endpoint for quick file upload without edit session.
    Commits directly to main branch.

    POST /api/editor/quick-upload-file/
    Form data:
    - file: <file>
    - target_path: "files" (optional, default: "files")
    - description: "File description" (optional)
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Upload file and commit directly to main branch."""
        # Validate input
        serializer = QuickUploadFileSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-QUICK-UPLOAD-VAL01")

        data = serializer.validated_data
        uploaded_file = data['file']
        target_path = data.get('target_path', 'files')
        description = data.get('description', '')

        try:
            # Get authenticated user
            user = request.user

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            file_ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
            unique_id = str(uuid.uuid4())[:8]
            base_name = Path(uploaded_file.name).stem if uploaded_file.name else 'file'
            filename = f"{base_name}-{timestamp}-{unique_id}.{file_ext}" if file_ext else f"{base_name}-{timestamp}-{unique_id}"

            # AIDEV-NOTE: quick-upload-path; Files stored in target_path (default: files/)
            # Clean up target_path - remove trailing slashes and handle empty paths
            target_path = target_path.strip('/')
            if target_path:
                file_path = f"{target_path}/{filename}"
            else:
                file_path = filename

            # Determine if file is binary
            text_extensions = {'md', 'txt', 'json', 'xml', 'html', 'css', 'js', 'py', 'yml', 'yaml', 'toml', 'ini', 'conf', 'log', 'csv', 'tsv'}
            is_binary = file_ext not in text_extensions

            # Save file to repository
            repo = get_repository()
            repo_path = repo.repo_path
            if target_path:
                full_file_dir = repo_path / target_path
            else:
                full_file_dir = repo_path
            full_file_dir.mkdir(parents=True, exist_ok=True)

            # Write file
            full_file_path = full_file_dir / filename
            with open(full_file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # Commit file directly to main
            commit_message = f"Upload file: {filename}"
            if description:
                commit_message += f" ({description})"

            repo.commit_changes(
                branch_name='main',
                file_path=file_path,
                content='',  # File is already written to disk
                commit_message=commit_message,
                user_info=get_user_info_for_commit(user),
                user=user,
                is_binary=True  # Flag to skip content write
            )

            # AIDEV-NOTE: rebuild-after-upload; Partial rebuild for directory listings (incremental-rebuild)
            logger.info(f'Triggering partial rebuild after file upload [EDITOR-QUICK-UPLOAD-REBUILD01]')
            try:
                repo.write_files_to_disk('main', [file_path], user)
                logger.info(f'Partial rebuild completed after file upload [EDITOR-QUICK-UPLOAD-REBUILD02]')
            except Exception as rebuild_error:
                logger.error(f'Partial rebuild failed after file upload: {rebuild_error} [EDITOR-QUICK-UPLOAD-REBUILD03]', exc_info=True)
                # Don't fail the upload if rebuild fails

            # Generate markdown link syntax for the file
            markdown_syntax = f"[{uploaded_file.name}]({file_path})"

            logger.info(f'User {user.id} ({user.username}) quick uploaded file: {filename} ({uploaded_file.size} bytes) [EDITOR-QUICK-UPLOAD01]')

            return success_response(
                data={
                    'filename': filename,
                    'path': file_path,
                    'markdown': markdown_syntax,
                    'file_size_bytes': uploaded_file.size,
                    'is_binary': is_binary
                },
                message=f"File '{filename}' uploaded successfully",
                status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            response, should_rollback = handle_exception(
                e, "quick upload file", "EDITOR-QUICK-UPLOAD02",
                "Failed to upload file. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class ConflictsListAPIView(APIView):
    """
    API endpoint to get list of all unresolved conflicts.

    GET /editor/api/conflicts/
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """Get list of conflicts without modifying data."""
        try:
            repo = get_repository()
            conflicts_data = repo.get_conflicts()

            # Augment with EditSession information
            for conflict in conflicts_data['conflicts']:
                branch_name = conflict['branch_name']

                # Get associated EditSession
                try:
                    session = EditSession.objects.filter(
                        branch_name=branch_name,
                        is_active=True
                    ).first()

                    if session:
                        conflict['session_id'] = session.id
                        conflict['user_name'] = session.user.username if session.user else 'Unknown'
                        conflict['file_path'] = session.file_path
                    else:
                        conflict['session_id'] = None
                        conflict['user_name'] = 'Unknown'
                        conflict['file_path'] = conflict['file_paths'][0] if conflict['file_paths'] else 'unknown'
                except Exception as e:
                    logger.warning(f'Failed to get session for {branch_name}: {str(e)}')
                    conflict['session_id'] = None
                    conflict['user_name'] = 'Unknown'
                    conflict['file_path'] = conflict['file_paths'][0] if conflict['file_paths'] else 'unknown'

            logger.info(f"Returned {len(conflicts_data['conflicts'])} conflicts [EDITOR-CONFLICT01]")

            return success_response(
                data=conflicts_data,
                message=f"Found {len(conflicts_data['conflicts'])} unresolved conflicts"
            )

        except Exception as e:
            response, _ = handle_exception(
                e, "get conflicts list", "EDITOR-CONFLICT02",
                "Failed to retrieve conflicts list. Please try again."
            )
            return response


class ConflictVersionsAPIView(APIView):
    """
    API endpoint to get three-way diff versions for conflict resolution.

    GET /editor/api/conflicts/versions/<session_id>/<file_path>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id, file_path):
        """Get conflict versions for resolution."""
        try:
            # Get edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)

            repo = get_repository()
            versions = repo.get_conflict_versions(session.branch_name, file_path)

            logger.info(f'Retrieved conflict versions for session {session_id}: {file_path} [EDITOR-CONFLICT03]')

            return success_response(
                data=versions,
                message=f"Retrieved conflict versions for '{file_path}'"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-CONFLICT04]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or inactive",
                error_code="EDITOR-CONFLICT-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, _ = handle_exception(
                e, "get conflict versions", "EDITOR-CONFLICT05",
                "Failed to retrieve conflict versions. Please try again."
            )
            return response


class ResolveConflictAPIView(APIView):
    """
    API endpoint to resolve a conflict.

    POST /editor/api/conflicts/resolve/
    {
        "session_id": 456,
        "file_path": "docs/page.md",
        "resolution_content": "resolved content...",
        "conflict_type": "text"  // or "image_mine", "image_theirs", "binary_mine", "binary_theirs"
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Resolve conflict with atomic transaction support."""
        # Validate input using serializer
        serializer = ResolveConflictSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-RESOLVE-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']
        file_path = data['file_path']
        resolution_content = data['resolution_content']
        conflict_type = data.get('conflict_type', 'text')

        # AIDEV-NOTE: security; Additional backend path validation to prevent path injection
        # Ensure file_path is within repository bounds
        from pathlib import Path as PathlibPath
        try:
            # Normalize path and check for traversal
            safe_path = PathlibPath(file_path)
            if safe_path.is_absolute() or '..' in safe_path.parts:
                logger.warning(f'Path traversal attempt in conflict resolution: {file_path} [EDITOR-RESOLVE-PATH01]')
                return validation_error_response(
                    {'file_path': 'Invalid file path: must be relative and within repository'},
                    "EDITOR-RESOLVE-VAL02"
                )
        except Exception as path_error:
            logger.warning(f'Invalid file path in conflict resolution: {file_path} - {path_error} [EDITOR-RESOLVE-PATH02]')
            return validation_error_response(
                {'file_path': 'Invalid file path format'},
                "EDITOR-RESOLVE-VAL03"
            )

        temp_file_path = None
        try:
            # Get edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)

            # Determine if binary
            is_binary = conflict_type in ['image_mine', 'image_theirs', 'binary_mine', 'binary_theirs']

            # For binary files, resolution_content should be a path to the chosen file
            # For text files, it's the actual resolved content
            if is_binary and conflict_type in ['image_theirs', 'binary_theirs']:
                # User chose the 'theirs' version (main branch)
                # We need to get that file from main branch
                repo = get_repository()
                theirs_content = repo.get_file_content_binary(file_path, branch='main')

                # AIDEV-NOTE: security; Use secure temp file handling with cleanup
                # Write to secure temp location for binary handling
                try:
                    # Create secure temporary file (mode 0600, unique name)
                    temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tmp', prefix='gitwiki_conflict_')
                    temp_file_path = temp_file.name
                    temp_file.write(theirs_content)
                    temp_file.close()
                    resolution_content = temp_file_path
                    logger.info(f'User {session.user.id} ({session.user.username}) prepared binary file for conflict resolution: {file_path} ({len(theirs_content)} bytes) [EDITOR-CONFLICT-BIN01]')
                except Exception as temp_error:
                    logger.error(f'Failed to create temp file for binary conflict resolution: {temp_error} [EDITOR-CONFLICT-TEMP01]', exc_info=True)
                    raise

            repo = get_repository()
            result = repo.resolve_conflict(
                branch_name=session.branch_name,
                file_path=file_path,
                resolution_content=resolution_content,
                user_info=get_user_info_for_commit(session.user),
                is_binary=is_binary
            )

            if result['merged']:
                # Conflict resolved and merged successfully
                # Mark session as inactive
                session.mark_inactive()

                logger.info(f'User {session.user.id} ({session.user.username}) resolved conflict and merged for session {session_id}: {file_path} [EDITOR-CONFLICT06]')

                return success_response(
                    data={
                        'merged': True,
                        'commit_hash': result['commit_hash']
                    },
                    message=f"Conflict resolved and changes published for '{file_path}'"
                )
            else:
                # Conflict resolution applied but still has conflicts
                logger.warning(f'User {session.user.id} ({session.user.username}) conflict resolution incomplete for session {session_id}: {file_path} [EDITOR-CONFLICT07]')

                return Response({
                    'success': True,
                    'data': {
                        'merged': False,
                        'commit_hash': result['commit_hash'],
                        'still_conflicts': result['still_conflicts']
                    },
                    'error': {
                        'message': 'Conflict resolution applied but merge still has conflicts',
                        'code': 'EDITOR-CONFLICT-PARTIAL'
                    }
                }, status=status.HTTP_409_CONFLICT)

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-CONFLICT08]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or inactive",
                error_code="EDITOR-CONFLICT-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "resolve conflict", "EDITOR-CONFLICT09",
                "Failed to resolve conflict. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response
        finally:
            # Clean up temporary file if it was created
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f'Cleaned up temp file: {temp_file_path} [EDITOR-CONFLICT-CLEANUP01]')
                except Exception as cleanup_error:
                    logger.warning(f'Failed to clean up temp file {temp_file_path}: {cleanup_error} [EDITOR-CONFLICT-CLEANUP02]')


class DeleteFileAPIView(APIView):
    """
    API endpoint for file deletion.

    POST /editor/api/delete-file/
    {
        "file_path": "docs/page.md",
        "commit_message": "Delete old file"  // optional
    }

    AIDEV-NOTE: file-delete-api; Deletes files from main branch and triggers static rebuild
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Delete file with atomic transaction support."""
        serializer = DeleteFileSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer.errors,
                error_code="EDITOR-DELETE-VAL01"
            )

        validated_data = serializer.validated_data
        file_path = validated_data['file_path']
        commit_message = validated_data.get('commit_message', f"Delete {file_path}")

        try:
            # Get authenticated user
            user = request.user

            # Delete file from repository
            repo = get_repository()
            result = repo.delete_file(
                file_path=file_path,
                commit_message=commit_message,
                user_info=get_user_info_for_commit(user),
                user=user,
                branch_name='main'
            )

            logger.info(f'User {user.id} ({user.username}) deleted file: {file_path} [EDITOR-DELETE01]')

            # Trigger partial rebuild for directory listings
            logger.info(f'Triggering partial rebuild after file deletion [EDITOR-DELETE-REBUILD01]')
            try:
                # Get all files in parent directory for rebuild
                parent_path = str(Path(file_path).parent)
                if parent_path == '.':
                    parent_path = ''

                # Get list of markdown files in the parent directory
                from pathlib import Path as PathLib
                parent_dir = repo.repo_path / parent_path if parent_path else repo.repo_path
                if parent_dir.exists() and parent_dir.is_dir():
                    md_files = []
                    for item in parent_dir.iterdir():
                        if item.is_file() and item.suffix == '.md':
                            rel_path = str(item.relative_to(repo.repo_path))
                            md_files.append(rel_path)

                    if md_files:
                        repo.write_files_to_disk('main', md_files, user)
                        logger.info(f'Partial rebuild completed after file deletion [EDITOR-DELETE-REBUILD02]')
                    else:
                        logger.info(f'No markdown files to rebuild in {parent_path} [EDITOR-DELETE-REBUILD03]')
                else:
                    logger.warning(f'Parent directory not found for rebuild: {parent_path} [EDITOR-DELETE-REBUILD04]')
            except Exception as rebuild_error:
                logger.error(f'Partial rebuild failed after file deletion: {rebuild_error} [EDITOR-DELETE-REBUILD05]', exc_info=True)
                # Don't fail the delete if rebuild fails

            return success_response(
                data={
                    'commit_hash': result['commit_hash'],
                    'file_path': file_path
                },
                message=f"File '{file_path}' deleted successfully"
            )

        except GitRepositoryError as e:
            error_str = str(e).lower()

            # Check for specific error conditions and provide helpful messages
            if "does not exist" in error_str or "not found" in error_str:
                logger.warning(f'Attempted to delete non-existent file: {file_path} [EDITOR-DELETE-NOTFOUND]', exc_info=True)
                return error_response(
                    message=f"File not found: {file_path}",
                    error_code="EDITOR-DELETE-NOTFOUND",
                    status_code=status.HTTP_404_NOT_FOUND,
                    details={'file_path': file_path}
                )
            elif "permission" in error_str or "denied" in error_str:
                logger.error(f'Permission denied during file deletion: {file_path} [EDITOR-DELETE-PERMISSION]', exc_info=True)
                return error_response(
                    message="Permission denied. Unable to delete file from repository.",
                    error_code="EDITOR-DELETE-PERMISSION",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    details={'file_path': file_path}
                )
            elif "lock" in error_str or "conflict" in error_str:
                logger.error(f'Repository lock/conflict during file deletion: {file_path} [EDITOR-DELETE-LOCK]', exc_info=True)
                return error_response(
                    message="Repository is currently locked or has conflicts. Please try again in a moment.",
                    error_code="EDITOR-DELETE-LOCK",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    details={'file_path': file_path}
                )
            elif "branch" in error_str:
                logger.error(f'Branch issue during file deletion: {file_path} [EDITOR-DELETE-BRANCH]', exc_info=True)
                return error_response(
                    message="Repository branch error. Unable to delete file.",
                    error_code="EDITOR-DELETE-BRANCH",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    details={'file_path': file_path}
                )
            else:
                # Generic git error
                logger.error(f'Git operation failed during deletion: {str(e)} [EDITOR-DELETE03]', exc_info=True)
                return error_response(
                    message="Failed to delete file due to repository error. Please try again.",
                    error_code="EDITOR-DELETE03",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    details={'file_path': file_path}
                )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "delete file", "EDITOR-DELETE04",
                "Failed to delete file. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class DiscardDraftAPIView(APIView):
    """
    API endpoint to discard a draft session.

    POST /api/editor/discard/
    {
        "session_id": 123
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Discard a draft session and delete its branch."""
        # Validate input
        serializer = DiscardDraftSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-DISCARD-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']

        try:
            # Get the edit session (with user ownership check to prevent IDOR)
            session = EditSession.objects.get(id=session_id, is_active=True, user=request.user)
            file_path = session.file_path
            branch_name = session.branch_name

            # Mark session as inactive
            session.mark_inactive()
            logger.info(f'User {session.user.id} ({session.user.username}) discarded draft session {session_id} for {file_path} [EDITOR-DISCARD01]')

            # Try to delete the draft branch
            try:
                repo = get_repository()
                # Switch to main before deleting the branch
                repo.repo.heads.main.checkout()
                # Delete the draft branch
                repo.repo.delete_head(branch_name, force=True)
                logger.info(f'User {session.user.id} ({session.user.username}) deleted draft branch {branch_name} [EDITOR-DISCARD02]')
            except Exception as e:
                # Branch deletion is not critical - session is already inactive
                logger.warning(f'Failed to delete branch {branch_name}: {e} [EDITOR-DISCARD03]')

            return success_response(
                data={
                    'session_id': session_id,
                    'file_path': file_path,
                    'branch_name': branch_name
                },
                message=f"Draft for '{file_path}' discarded successfully"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Session not found: {session_id} [EDITOR-DISCARD-NOTFOUND]', exc_info=True)
            return error_response(
                message=f"Edit session {session_id} not found or already discarded",
                error_code="EDITOR-DISCARD-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'session_id': session_id}
            )
        except Exception as e:
            response, should_rollback = handle_exception(
                e, "discard draft", "EDITOR-DISCARD04",
                "Failed to discard draft. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response
