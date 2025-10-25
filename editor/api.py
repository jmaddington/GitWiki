"""
API views for Editor Service.

AIDEV-NOTE: editor-api; All editor operations including start, commit, publish, and image upload
"""

import os
import uuid
import markdown
import logging
from datetime import datetime
from pathlib import Path

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny  # MVP: Open access
from django.contrib.auth.models import User
from django.conf import settings

from git_service.git_operations import get_repository, GitRepositoryError
from .models import EditSession
from .serializers import (
    StartEditSerializer,
    ValidateMarkdownSerializer,
    CommitDraftSerializer,
    PublishEditSerializer,
    UploadImageSerializer,
    DiscardDraftSerializer
)

logger = logging.getLogger(__name__)


class StartEditAPIView(APIView):
    """
    Start an edit session for a file.

    POST /api/editor/start/
    {
        "user_id": 123,
        "file_path": "docs/getting-started.md"
    }

    Returns:
    {
        "session_id": 456,
        "branch_name": "draft-123-abc456",
        "file_path": "docs/getting-started.md",
        "content": "# Current content...",
        "markdown_valid": true
    }
    """
    permission_classes = [AllowAny]  # MVP: Open access

    def post(self, request):
        serializer = StartEditSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        user_id = serializer.validated_data['user_id']
        file_path = serializer.validated_data['file_path']

        try:
            # Check if user exists
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if there's already an active session for this file
            existing_session = EditSession.get_user_session_for_file(user, file_path)
            if existing_session:
                logger.info(
                    f'Resuming existing edit session: {existing_session.id} [EDITOR-START01]'
                )
                # Return existing session
                repo = get_repository()
                try:
                    content = repo.get_file_content(file_path, existing_session.branch_name)
                except GitRepositoryError:
                    # File might not exist yet
                    content = ""

                return Response({
                    'session_id': existing_session.id,
                    'branch_name': existing_session.branch_name,
                    'file_path': file_path,
                    'content': content,
                    'markdown_valid': True,
                    'resumed': True
                }, status=status.HTTP_200_OK)

            # Create new draft branch
            repo = get_repository()
            branch_result = repo.create_draft_branch(user_id, user=user)
            branch_name = branch_result['branch_name']

            # Create edit session
            session = EditSession.objects.create(
                user=user,
                file_path=file_path,
                branch_name=branch_name,
                is_active=True
            )

            # Get current file content from main branch (if it exists)
            try:
                content = repo.get_file_content(file_path, 'main')
            except GitRepositoryError:
                # File doesn't exist yet, start with empty content
                content = ""
                logger.info(f'Starting new file: {file_path} [EDITOR-START02]')

            logger.info(
                f'Created edit session {session.id} for user {user_id}: '
                f'{file_path} on {branch_name} [EDITOR-START03]'
            )

            return Response({
                'session_id': session.id,
                'branch_name': branch_name,
                'file_path': file_path,
                'content': content,
                'markdown_valid': True,
                'resumed': False
            }, status=status.HTTP_200_OK)

        except GitRepositoryError as e:
            logger.error(f'Git error starting edit session: {str(e)} [EDITOR-START04]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f'Unexpected error starting edit session: {str(e)} [EDITOR-START05]')
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValidateMarkdownAPIView(APIView):
    """
    Validate markdown syntax.

    POST /api/editor/validate/
    {
        "content": "# Markdown content..."
    }

    Returns:
    {
        "valid": true,
        "errors": [],
        "warnings": []
    }
    """
    permission_classes = [AllowAny]  # MVP: Open access

    def post(self, request):
        serializer = ValidateMarkdownSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        content = serializer.validated_data['content']

        # AIDEV-NOTE: markdown-validation; Using python-markdown for validation
        errors = []
        warnings = []

        try:
            # Try to parse markdown
            md = markdown.Markdown(extensions=['extra', 'codehilite'])
            md.convert(content)

            # Basic validation checks
            if content:
                lines = content.split('\n')

                # Check for unclosed code blocks
                code_block_count = content.count('```')
                if code_block_count % 2 != 0:
                    warnings.append("Unclosed code block detected")

                # Check for unclosed inline code
                for i, line in enumerate(lines, 1):
                    inline_code_count = line.count('`')
                    if inline_code_count % 2 != 0:
                        warnings.append(f"Line {i}: Unclosed inline code")

            valid = len(errors) == 0

            return Response({
                'valid': valid,
                'errors': errors,
                'warnings': warnings
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Markdown validation error: {str(e)} [EDITOR-VALIDATE01]')
            return Response({
                'valid': False,
                'errors': [str(e)],
                'warnings': warnings
            }, status=status.HTTP_200_OK)


class CommitDraftAPIView(APIView):
    """
    Commit draft changes to the draft branch.

    POST /api/editor/commit/
    {
        "session_id": 456,
        "content": "# Updated content...",
        "commit_message": "Update getting started guide"
    }

    Returns:
    {
        "success": true,
        "commit_hash": "abc123",
        "branch_name": "draft-123-abc456"
    }
    """
    permission_classes = [AllowAny]  # MVP: Open access

    def post(self, request):
        serializer = CommitDraftSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        session_id = serializer.validated_data['session_id']
        content = serializer.validated_data['content']
        commit_message = serializer.validated_data['commit_message']

        try:
            # Get edit session
            try:
                session = EditSession.objects.get(id=session_id, is_active=True)
            except EditSession.DoesNotExist:
                return Response(
                    {'error': 'Edit session not found or inactive'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Validate markdown (hard error on commit)
            md = markdown.Markdown(extensions=['extra', 'codehilite'])
            try:
                md.convert(content)
            except Exception as e:
                logger.warning(f'Invalid markdown on commit: {str(e)} [EDITOR-COMMIT01]')
                return Response(
                    {'error': f'Invalid markdown: {str(e)}'},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            # Commit changes via Git Service
            repo = get_repository()
            commit_result = repo.commit_changes(
                branch_name=session.branch_name,
                file_path=session.file_path,
                content=content,
                commit_message=commit_message,
                user_info={
                    'name': session.user.get_full_name() or session.user.username,
                    'email': session.user.email or f'{session.user.username}@example.com'
                },
                user=session.user
            )

            # Update session timestamp
            session.touch()

            logger.info(
                f'Committed draft for session {session_id}: '
                f'{commit_result["commit_hash"]} [EDITOR-COMMIT02]'
            )

            return Response({
                'success': True,
                'commit_hash': commit_result['commit_hash'],
                'branch_name': session.branch_name
            }, status=status.HTTP_200_OK)

        except GitRepositoryError as e:
            logger.error(f'Git error committing draft: {str(e)} [EDITOR-COMMIT03]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f'Unexpected error committing draft: {str(e)} [EDITOR-COMMIT04]')
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublishEditAPIView(APIView):
    """
    Publish draft to main branch.

    POST /api/editor/publish/
    {
        "session_id": 456,
        "auto_push": true
    }

    Returns (success):
    {
        "success": true,
        "published": true,
        "commit_hash": "def456",
        "url": "/main/docs/getting-started"
    }

    Returns (conflict):
    {
        "success": false,
        "conflict": true,
        "conflict_details": {
            "file_path": "docs/getting-started.md",
            "resolution_url": "/conflicts/resolve/draft-123-abc456"
        }
    }
    """
    permission_classes = [AllowAny]  # MVP: Open access

    def post(self, request):
        serializer = PublishEditSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        session_id = serializer.validated_data['session_id']
        auto_push = serializer.validated_data['auto_push']

        try:
            # Get edit session
            try:
                session = EditSession.objects.get(id=session_id, is_active=True)
            except EditSession.DoesNotExist:
                return Response(
                    {'error': 'Edit session not found or inactive'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Publish via Git Service
            repo = get_repository()
            publish_result = repo.publish_draft(
                branch_name=session.branch_name,
                auto_push=auto_push,
                user=session.user
            )

            if publish_result['success']:
                # Close edit session
                session.mark_inactive()

                # Generate URL for published page
                page_url = f"/main/{session.file_path.replace('.md', '')}"

                logger.info(
                    f'Published draft for session {session_id}: '
                    f'{session.branch_name} -> main [EDITOR-PUBLISH01]'
                )

                return Response({
                    'success': True,
                    'published': True,
                    'commit_hash': publish_result.get('commit_hash'),
                    'url': page_url
                }, status=status.HTTP_200_OK)
            else:
                # Conflict detected
                logger.warning(
                    f'Conflict detected publishing session {session_id}: '
                    f'{session.branch_name} [EDITOR-PUBLISH02]'
                )

                return Response({
                    'success': False,
                    'conflict': True,
                    'conflict_details': {
                        'file_path': session.file_path,
                        'conflicts': publish_result.get('conflicts', []),
                        'resolution_url': f'/conflicts/resolve/{session.branch_name}'
                    }
                }, status=status.HTTP_409_CONFLICT)

        except GitRepositoryError as e:
            logger.error(f'Git error publishing draft: {str(e)} [EDITOR-PUBLISH03]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f'Unexpected error publishing draft: {str(e)} [EDITOR-PUBLISH04]')
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadImageAPIView(APIView):
    """
    Upload an image for the draft branch.

    POST /api/editor/upload-image/
    Content-Type: multipart/form-data

    session_id: 456
    image: [file]
    alt_text: "Screenshot of feature"

    Returns:
    {
        "success": true,
        "filename": "screenshot-20251025-100500.png",
        "path": "images/draft-123-abc456/screenshot-20251025-100500.png",
        "markdown": "![Screenshot of feature](images/draft-123-abc456/screenshot-20251025-100500.png)",
        "file_size_bytes": 245000
    }
    """
    permission_classes = [AllowAny]  # MVP: Open access

    def post(self, request):
        serializer = UploadImageSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        session_id = serializer.validated_data['session_id']
        image_file = serializer.validated_data['image']
        alt_text = serializer.validated_data.get('alt_text', '')

        try:
            # Get edit session
            try:
                session = EditSession.objects.get(id=session_id, is_active=True)
            except EditSession.DoesNotExist:
                return Response(
                    {'error': 'Edit session not found or inactive'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            ext = os.path.splitext(image_file.name)[1]
            unique_id = str(uuid.uuid4())[:8]
            filename = f"image-{timestamp}-{unique_id}{ext}"

            # AIDEV-NOTE: image-path-structure; Images stored in images/{branch_name}/
            image_dir = f"images/{session.branch_name}"
            image_path = f"{image_dir}/{filename}"

            # Create images directory in repository
            repo = get_repository()
            repo_image_dir = repo.repo_path / image_dir
            repo_image_dir.mkdir(parents=True, exist_ok=True)

            # Save image file
            repo_image_path = repo.repo_path / image_path
            with open(repo_image_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)

            # Commit image to git
            commit_message = f"Add image: {filename}"
            repo.commit_changes(
                branch_name=session.branch_name,
                file_path=image_path,
                content=None,  # Binary file, already saved
                commit_message=commit_message,
                user_info={
                    'name': session.user.get_full_name() or session.user.username,
                    'email': session.user.email or f'{session.user.username}@example.com'
                },
                user=session.user,
                is_binary=True
            )

            # Generate markdown syntax
            markdown_syntax = f"![{alt_text}]({image_path})"

            logger.info(
                f'Uploaded image for session {session_id}: '
                f'{image_path} ({image_file.size} bytes) [EDITOR-IMAGE01]'
            )

            return Response({
                'success': True,
                'filename': filename,
                'path': image_path,
                'markdown': markdown_syntax,
                'file_size_bytes': image_file.size
            }, status=status.HTTP_200_OK)

        except GitRepositoryError as e:
            logger.error(f'Git error uploading image: {str(e)} [EDITOR-IMAGE02]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f'Unexpected error uploading image: {str(e)} [EDITOR-IMAGE03]')
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DiscardDraftAPIView(APIView):
    """
    Discard a draft and close the edit session.

    POST /api/editor/discard/
    {
        "session_id": 456
    }

    Returns:
    {
        "success": true,
        "message": "Draft discarded"
    }
    """
    permission_classes = [AllowAny]  # MVP: Open access

    def post(self, request):
        serializer = DiscardDraftSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        session_id = serializer.validated_data['session_id']

        try:
            # Get edit session
            try:
                session = EditSession.objects.get(id=session_id, is_active=True)
            except EditSession.DoesNotExist:
                return Response(
                    {'error': 'Edit session not found or inactive'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Mark session as inactive
            session.mark_inactive()

            logger.info(f'Discarded draft for session {session_id} [EDITOR-DISCARD01]')

            return Response({
                'success': True,
                'message': 'Draft discarded'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error discarding draft: {str(e)} [EDITOR-DISCARD02]')
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
