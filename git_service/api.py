"""
API views for Git Service.

AIDEV-NOTE: api-endpoints; REST API for git operations
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.contrib.auth.models import User
import logging

from .git_operations import get_repository, GitRepositoryError
from .serializers import (
    CreateBranchSerializer,
    CommitChangesSerializer,
    PublishDraftSerializer,
    GetFileSerializer
)

logger = logging.getLogger(__name__)


class CreateBranchAPIView(APIView):
    """
    API endpoint to create a new draft branch.

    POST /api/git/branch/create/
    {
        "user_id": 123
    }
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request):
        serializer = CreateBranchSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        user_id = serializer.validated_data['user_id']

        try:
            # Get user instance for logging
            user = None
            if request.user.is_authenticated:
                user = request.user

            # Create branch
            repo = get_repository()
            result = repo.create_draft_branch(user_id, user=user)

            logger.info(f'Branch created via API: {result["branch_name"]} [API-BRANCH01]')

            return Response(result, status=status.HTTP_200_OK)

        except GitRepositoryError as e:
            logger.error(f'Failed to create branch via API: {str(e)} [API-BRANCH02]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommitChangesAPIView(APIView):
    """
    API endpoint to commit changes to a draft branch.

    POST /api/git/commit/
    {
        "branch_name": "draft-123-abc456",
        "file_path": "docs/page.md",
        "content": "# Page Title\nContent...",
        "commit_message": "Update page",
        "user_info": {
            "name": "John Doe",
            "email": "john@example.com"
        }
    }
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request):
        serializer = CommitChangesSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        data = serializer.validated_data

        try:
            # Get user instance for logging
            user = None
            if request.user.is_authenticated:
                user = request.user

            # Commit changes
            repo = get_repository()
            result = repo.commit_changes(
                branch_name=data['branch_name'],
                file_path=data['file_path'],
                content=data['content'],
                commit_message=data['commit_message'],
                user_info=data['user_info'],
                user=user
            )

            logger.info(f'Changes committed via API: {result["commit_hash"][:8]} [API-COMMIT01]')

            return Response(result, status=status.HTTP_200_OK)

        except GitRepositoryError as e:
            logger.error(f'Failed to commit changes via API: {str(e)} [API-COMMIT02]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublishDraftAPIView(APIView):
    """
    API endpoint to publish a draft branch to main.

    POST /api/git/publish/
    {
        "branch_name": "draft-123-abc456",
        "auto_push": true
    }
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request):
        serializer = PublishDraftSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        data = serializer.validated_data

        try:
            # Get user instance for logging
            user = None
            if request.user.is_authenticated:
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
                logger.warning(f'Publish failed due to conflicts: {data["branch_name"]} [API-PUBLISH01]')
                return Response(result, status=status.HTTP_409_CONFLICT)

            logger.info(f'Draft published via API: {data["branch_name"]} [API-PUBLISH02]')

            return Response(result, status=status.HTTP_200_OK)

        except GitRepositoryError as e:
            logger.error(f'Failed to publish draft via API: {str(e)} [API-PUBLISH03]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetFileAPIView(APIView):
    """
    API endpoint to get file content from a branch.

    GET /api/git/file/?file_path=docs/page.md&branch=main
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        serializer = GetFileSerializer(data=request.query_params)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        data = serializer.validated_data

        try:
            repo = get_repository()
            content = repo.get_file_content(
                file_path=data['file_path'],
                branch=data['branch']
            )

            return Response(
                {
                    'file_path': data['file_path'],
                    'branch': data['branch'],
                    'content': content
                },
                status=status.HTTP_200_OK
            )

        except GitRepositoryError as e:
            logger.error(f'Failed to get file via API: {str(e)} [API-FILE01]')
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


class ListBranchesAPIView(APIView):
    """
    API endpoint to list all branches.

    GET /api/git/branches/?pattern=draft-*
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        pattern = request.query_params.get('pattern', None)

        try:
            repo = get_repository()
            branches = repo.list_branches(pattern=pattern)

            return Response(
                {'branches': branches},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f'Failed to list branches via API: {str(e)} [API-BRANCHES01]')
            return Response(
                {'error': 'Failed to list branches'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
