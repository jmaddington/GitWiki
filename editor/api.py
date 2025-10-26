"""
API views for Editor Service.

AIDEV-NOTE: editor-api; REST API for markdown editing workflow with standardized error handling
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from pathlib import Path
import logging
import markdown
import os
import uuid
from datetime import datetime

from .models import EditSession
from .serializers import (
    StartEditSerializer,
    SaveDraftSerializer,
    CommitDraftSerializer,
    PublishEditSerializer,
    ValidateMarkdownSerializer,
    UploadImageSerializer
)
from git_service.git_operations import get_repository, GitRepositoryError
from git_service.models import Configuration
from config.api_utils import (
    error_response,
    success_response,
    validation_error_response,
    handle_exception
)

logger = logging.getLogger(__name__)


class StartEditAPIView(APIView):
    """
    API endpoint to start editing a file.

    POST /api/editor/start/
    {
        "user_id": 123,
        "file_path": "docs/getting-started.md"
    }
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request):
        """Start an edit session with atomic transaction support."""
        # Validate input
        serializer = StartEditSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-START-VAL01")

        data = serializer.validated_data
        user_id = data['user_id']
        file_path = data['file_path']

        try:
            # Get or create user
            user, created = User.objects.get_or_create(
                id=user_id,
                defaults={'username': f'user_{user_id}'}
            )

            # Check if user already has an active session for this file
            existing_session = EditSession.get_user_session_for_file(user, file_path)
            if existing_session:
                # Resume existing session
                logger.info(f'Resuming existing edit session: {existing_session.id} [EDITOR-START01]')

                # Get current content from branch
                repo = get_repository()
                try:
                    content = repo.get_file_content(file_path, existing_session.branch_name)
                except GitRepositoryError:
                    # File doesn't exist in branch yet, get from main
                    try:
                        content = repo.get_file_content(file_path, 'main')
                    except GitRepositoryError:
                        # File doesn't exist anywhere, start with empty content
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
                    message=f"Resumed edit session for '{file_path}'"
                )

            # Create new draft branch
            repo = get_repository()
            branch_result = repo.create_draft_branch(user_id, user=user)

            # Create edit session
            session = EditSession.objects.create(
                user=user,
                file_path=file_path,
                branch_name=branch_result['branch_name']
            )

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
    permission_classes = [IsAuthenticatedOrReadOnly]

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
            # Get edit session
            session = EditSession.objects.get(id=session_id, is_active=True)

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
            logger.error(f'Edit session not found: {session_id} [EDITOR-SAVE02]')
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
    permission_classes = [IsAuthenticatedOrReadOnly]

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
            # Get edit session
            session = EditSession.objects.get(id=session_id, is_active=True)

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

            # Commit to Git
            repo = get_repository()
            commit_result = repo.commit_changes(
                branch_name=session.branch_name,
                file_path=session.file_path,
                content=content,
                commit_message=commit_message,
                user_info={
                    'name': session.user.username,
                    'email': session.user.email or f'{session.user.username}@gitwiki.local'
                },
                user=session.user
            )

            # Update session
            session.touch()

            logger.info(f'Committed draft for session {session_id}: {commit_result["commit_hash"][:8]} [EDITOR-COMMIT01]')

            return success_response(
                data={
                    'commit_hash': commit_result['commit_hash'],
                    'branch_name': session.branch_name
                },
                message=f"Changes committed to {session.file_path}"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-COMMIT02]')
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
    permission_classes = [IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request):
        """Publish edit to main branch with atomic transaction support."""
        # Validate input
        serializer = PublishEditSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "EDITOR-PUBLISH-VAL01")

        data = serializer.validated_data
        session_id = data['session_id']
        auto_push = data['auto_push']

        try:
            # Get edit session
            session = EditSession.objects.get(id=session_id, is_active=True)

            # Publish to main via Git Service
            repo = get_repository()
            publish_result = repo.publish_draft(
                branch_name=session.branch_name,
                user=session.user,
                auto_push=auto_push
            )

            # Check for conflicts
            if not publish_result['success'] and 'conflicts' in publish_result:
                logger.warning(f'Publish failed due to conflicts: {session.branch_name} [EDITOR-PUBLISH01]')
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

            logger.info(f'Published edit session {session_id} to main [EDITOR-PUBLISH02]')

            return success_response(
                data={
                    'published': True,
                    'url': f'/wiki/{session.file_path.replace(".md", ".html")}'
                },
                message=f"Successfully published '{session.file_path}' to main branch"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-PUBLISH03]')
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
    permission_classes = [IsAuthenticatedOrReadOnly]

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
            # Get edit session
            session = EditSession.objects.get(id=session_id, is_active=True)

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
                user_info={
                    'name': session.user.username,
                    'email': session.user.email or f'{session.user.username}@gitwiki.local'
                },
                user=session.user,
                is_binary=True  # Flag to skip content write
            )

            # Generate markdown syntax
            markdown_syntax = f"![{alt_text}]({image_path})"

            logger.info(f'Uploaded image for session {session_id}: {filename} [EDITOR-UPLOAD01]')

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
            logger.error(f'Edit session not found: {session_id} [EDITOR-UPLOAD02]')
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
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, session_id, file_path):
        """Get conflict versions for resolution."""
        try:
            # Get edit session
            session = EditSession.objects.get(id=session_id, is_active=True)

            repo = get_repository()
            versions = repo.get_conflict_versions(session.branch_name, file_path)

            logger.info(f'Retrieved conflict versions for session {session_id}: {file_path} [EDITOR-CONFLICT03]')

            return success_response(
                data=versions,
                message=f"Retrieved conflict versions for '{file_path}'"
            )

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-CONFLICT04]')
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
    permission_classes = [IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request):
        """Resolve conflict with atomic transaction support."""
        # Validate required fields
        session_id = request.data.get('session_id')
        file_path = request.data.get('file_path')
        resolution_content = request.data.get('resolution_content')
        conflict_type = request.data.get('conflict_type', 'text')

        if not all([session_id, file_path, resolution_content]):
            return error_response(
                message="Missing required fields",
                error_code="EDITOR-RESOLVE-VAL01",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={
                    'required_fields': ['session_id', 'file_path', 'resolution_content'],
                    'missing': [f for f in ['session_id', 'file_path', 'resolution_content']
                               if not request.data.get(f)]
                }
            )

        try:
            # Get edit session
            session = EditSession.objects.get(id=session_id, is_active=True)

            # Determine if binary
            is_binary = conflict_type in ['image_mine', 'image_theirs', 'binary_mine', 'binary_theirs']

            # For binary files, resolution_content should be a path to the chosen file
            # For text files, it's the actual resolved content
            if is_binary and conflict_type in ['image_theirs', 'binary_theirs']:
                # User chose the 'theirs' version (main branch)
                # We need to get that file from main branch
                repo = get_repository()
                theirs_content = repo.get_file_content(file_path, branch='main')

                # Write to temp location for binary handling
                temp_path = Path(f'/tmp/{uuid.uuid4()}.tmp')
                temp_path.write_bytes(theirs_content.encode() if isinstance(theirs_content, str) else theirs_content)
                resolution_content = str(temp_path)

            # User info
            user_info = {
                'name': session.user.get_full_name() or session.user.username if session.user else 'Unknown',
                'email': session.user.email if session.user else 'unknown@example.com'
            }

            repo = get_repository()
            result = repo.resolve_conflict(
                branch_name=session.branch_name,
                file_path=file_path,
                resolution_content=resolution_content,
                user_info=user_info,
                is_binary=is_binary
            )

            if result['merged']:
                # Conflict resolved and merged successfully
                # Mark session as inactive
                session.mark_inactive()

                logger.info(f'Conflict resolved and merged for session {session_id}: {file_path} [EDITOR-CONFLICT06]')

                return success_response(
                    data={
                        'merged': True,
                        'commit_hash': result['commit_hash']
                    },
                    message=f"Conflict resolved and changes published for '{file_path}'"
                )
            else:
                # Conflict resolution applied but still has conflicts
                logger.warning(f'Conflict resolution incomplete for session {session_id}: {file_path} [EDITOR-CONFLICT07]')

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
            logger.error(f'Edit session not found: {session_id} [EDITOR-CONFLICT08]')
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
