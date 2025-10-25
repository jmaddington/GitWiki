"""
API views for Editor Service.

AIDEV-NOTE: editor-api; REST API for markdown editing workflow
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.contrib.auth.models import User
from django.utils import timezone
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

    def post(self, request):
        serializer = StartEditSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

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

                return Response({
                    'session_id': existing_session.id,
                    'branch_name': existing_session.branch_name,
                    'file_path': file_path,
                    'content': content,
                    'created_at': existing_session.created_at,
                    'last_modified': existing_session.last_modified,
                    'resumed': True
                }, status=status.HTTP_200_OK)

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

            return Response({
                'session_id': session.id,
                'branch_name': branch_result['branch_name'],
                'file_path': file_path,
                'content': content,
                'created_at': session.created_at,
                'last_modified': session.last_modified,
                'resumed': False
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Failed to start edit session: {str(e)} [EDITOR-START03]')
            return Response(
                {'error': f'Failed to start edit session: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

    def post(self, request):
        serializer = SaveDraftSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

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

            return Response({
                'success': True,
                'saved_at': session.last_modified,
                'markdown_valid': validation['valid'],
                'validation_errors': validation.get('errors', []),
                'validation_warnings': validation.get('warnings', [])
            }, status=status.HTTP_200_OK)

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-SAVE02]')
            return Response(
                {'error': 'Edit session not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f'Failed to save draft: {str(e)} [EDITOR-SAVE03]')
            return Response(
                {'error': f'Failed to save draft: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

    def post(self, request):
        serializer = CommitDraftSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

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
                return Response(
                    {
                        'error': 'Invalid markdown',
                        'validation_errors': validation.get('errors', [])
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
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

            return Response({
                'success': True,
                'commit_hash': commit_result['commit_hash'],
                'branch_name': session.branch_name
            }, status=status.HTTP_200_OK)

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-COMMIT02]')
            return Response(
                {'error': 'Edit session not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        except GitRepositoryError as e:
            logger.error(f'Failed to commit draft: {str(e)} [EDITOR-COMMIT03]')
            return Response(
                {'error': f'Failed to commit: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f'Unexpected error committing draft: {str(e)} [EDITOR-COMMIT04]')
            return Response(
                {'error': f'Failed to commit: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

    def post(self, request):
        serializer = PublishEditSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

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
                    'conflict': True,
                    'conflict_details': {
                        'file_path': session.file_path,
                        'conflicts': publish_result['conflicts'],
                        'resolution_url': f'/editor/conflicts/{session.branch_name}'
                    }
                }, status=status.HTTP_409_CONFLICT)

            # Success - close edit session
            session.mark_inactive()

            logger.info(f'Published edit session {session_id} to main [EDITOR-PUBLISH02]')

            return Response({
                'success': True,
                'published': True,
                'url': f'/wiki/{session.file_path.replace(".md", ".html")}'
            }, status=status.HTTP_200_OK)

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-PUBLISH03]')
            return Response(
                {'error': 'Edit session not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        except GitRepositoryError as e:
            logger.error(f'Failed to publish edit: {str(e)} [EDITOR-PUBLISH04]')
            return Response(
                {'error': f'Failed to publish: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f'Unexpected error publishing edit: {str(e)} [EDITOR-PUBLISH05]')
            return Response(
                {'error': f'Failed to publish: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        serializer = ValidateMarkdownSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        content = serializer.validated_data['content']

        # Use the same validation as SaveDraftAPIView
        save_view = SaveDraftAPIView()
        validation = save_view._validate_markdown(content)

        return Response(validation, status=status.HTTP_200_OK)


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

    def post(self, request):
        serializer = UploadImageSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

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

            return Response({
                'success': True,
                'filename': filename,
                'path': image_path,
                'markdown': markdown_syntax,
                'file_size_bytes': image_file.size
            }, status=status.HTTP_200_OK)

        except EditSession.DoesNotExist:
            logger.error(f'Edit session not found: {session_id} [EDITOR-UPLOAD02]')
            return Response(
                {'error': 'Edit session not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f'Failed to upload image: {str(e)} [EDITOR-UPLOAD03]')
            return Response(
                {'error': f'Failed to upload image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
