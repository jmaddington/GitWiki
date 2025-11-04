"""
API views for Git Service.

AIDEV-NOTE: api-endpoints; REST API for git operations with standardized error handling
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.contrib.auth.models import User
from django.db import transaction
import logging

from .git_operations import get_repository, GitRepositoryError
from .serializers import (
    CreateBranchSerializer,
    CommitChangesSerializer,
    PublishDraftSerializer,
    GetFileSerializer
)
from config.api_utils import (
    error_response,
    success_response,
    validation_error_response,
    handle_exception,
    get_user_info_for_commit
)

logger = logging.getLogger(__name__)


class CreateBranchAPIView(APIView):
    """
    API endpoint to create a new draft branch.

    POST /api/git/branch/create/
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Create a new draft branch with atomic transaction support."""
        # Get authenticated user
        user = request.user

        try:
            # Create branch
            repo = get_repository()
            result = repo.create_draft_branch(user.id, user=user)

            logger.info(f'User {user.id} ({user.username}) created branch via API: {result["branch_name"]} [API-BRANCH01]')

            return success_response(
                data=result,
                message=f"Draft branch '{result['branch_name']}' created successfully"
            )

        except Exception as e:
            response, should_rollback = handle_exception(
                e, "create branch", "API-BRANCH02",
                "Failed to create draft branch. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class CommitChangesAPIView(APIView):
    """
    API endpoint to commit changes to a draft branch.

    POST /api/git/commit/
    {
        "branch_name": "draft-123-abc456",
        "file_path": "docs/page.md",
        "content": "# Page Title\nContent...",
        "commit_message": "Update page"
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Commit changes to a draft branch with atomic transaction support."""
        # Validate input
        serializer = CommitChangesSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "API-COMMIT-VAL01")

        data = serializer.validated_data

        try:
            # Get authenticated user
            user = request.user

            # Commit changes
            repo = get_repository()
            result = repo.commit_changes(
                branch_name=data['branch_name'],
                file_path=data['file_path'],
                content=data['content'],
                commit_message=data['commit_message'],
                user_info=get_user_info_for_commit(user),
                user=user
            )

            logger.info(f'User {user.id} ({user.username}) committed changes via API: {result["commit_hash"][:8]} to {data["file_path"]} [API-COMMIT01]')

            return success_response(
                data=result,
                message=f"Changes committed to {data['file_path']}"
            )

        except Exception as e:
            response, should_rollback = handle_exception(
                e, "commit changes", "API-COMMIT02",
                f"Failed to commit changes to {data.get('file_path', 'file')}. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class PublishDraftAPIView(APIView):
    """
    API endpoint to publish a draft branch to main.

    POST /api/git/publish/
    {
        "branch_name": "draft-123-abc456",
        "auto_push": true
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Publish a draft branch to main with atomic transaction support."""
        # Validate input
        serializer = PublishDraftSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "API-PUBLISH-VAL01")

        data = serializer.validated_data

        try:
            # Get authenticated user
            user = request.user

            # Publish draft
            repo = get_repository()
            result = repo.publish_draft(
                branch_name=data['branch_name'],
                user=user,
                auto_push=data['auto_push']
            )

            # If there were conflicts, return 409
            if not result['success'] and 'conflicts' in result:
                logger.warning(f'User {user.id} ({user.username}) publish failed due to conflicts: {data["branch_name"]} [API-PUBLISH01]')
                # Add success=False to maintain standard format
                result['success'] = False
                result['error'] = {
                    'message': 'Cannot publish due to merge conflicts',
                    'code': 'API-PUBLISH-CONFLICT',
                    'conflicts': result['conflicts']
                }
                return Response(result, status=status.HTTP_409_CONFLICT)

            logger.info(f'User {user.id} ({user.username}) published draft via API: {data["branch_name"]} [API-PUBLISH02]')

            return success_response(
                data=result,
                message=f"Draft branch '{data['branch_name']}' published successfully"
            )

        except Exception as e:
            response, should_rollback = handle_exception(
                e, "publish draft", "API-PUBLISH03",
                f"Failed to publish draft branch '{data.get('branch_name', 'unknown')}'. Please try again."
            )
            if should_rollback:
                transaction.set_rollback(True)
            return response


class GetFileAPIView(APIView):
    """
    API endpoint to get file content from a branch.

    GET /api/git/file/?file_path=docs/page.md&branch=main
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """Get file content from a specific branch."""
        # Validate input
        serializer = GetFileSerializer(data=request.query_params)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors, "API-FILE-VAL01")

        data = serializer.validated_data

        try:
            repo = get_repository()
            content = repo.get_file_content(
                file_path=data['file_path'],
                branch=data['branch']
            )

            return success_response(
                data={
                    'file_path': data['file_path'],
                    'branch': data['branch'],
                    'content': content
                },
                message=f"Retrieved file '{data['file_path']}' from branch '{data['branch']}'"
            )

        except GitRepositoryError:
            # File not found is expected - return 404
            logger.warning(f'File not found via API: {data["file_path"]} on {data["branch"]} [API-FILE01]')
            return error_response(
                message=f"File '{data['file_path']}' not found in branch '{data['branch']}'",
                error_code="API-FILE-NOTFOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={'file_path': data['file_path'], 'branch': data['branch']}
            )
        except Exception as e:
            response, _ = handle_exception(
                e, "get file", "API-FILE02",
                f"Failed to retrieve file '{data.get('file_path', 'unknown')}'"
            )
            return response


class ListBranchesAPIView(APIView):
    """
    API endpoint to list all branches.

    GET /api/git/branches/?pattern=draft-*
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """List branches with optional pattern filter."""
        pattern = request.query_params.get('pattern', None)

        try:
            repo = get_repository()
            branches = repo.list_branches(pattern=pattern)

            message = f"Found {len(branches)} branches"
            if pattern:
                message += f" matching pattern '{pattern}'"

            return success_response(
                data={'branches': branches, 'count': len(branches)},
                message=message
            )

        except Exception as e:
            response, _ = handle_exception(
                e, "list branches", "API-BRANCHES01",
                "Failed to list branches. Please try again."
            )
            return response
