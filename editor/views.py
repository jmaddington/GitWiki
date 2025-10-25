"""
Views for Editor Service.

AIDEV-NOTE: editor-views; HTML views for editor UI
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import EditSession
from git_service.git_operations import get_repository, GitRepositoryError

logger = logging.getLogger(__name__)


def edit_page(request, file_path):
    """
    Render the editor page for a file.

    GET /editor/{file_path}

    If user is not authenticated in production, redirect to login.
    For MVP, we'll use a default user for testing.
    """
    # AIDEV-NOTE: auth-mvp; Using user_id from query param for MVP
    # In production, use request.user

    # Get or create default user for MVP
    user_id = request.GET.get('user_id', '1')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # Create default user for MVP
        user = User.objects.create_user(
            username='default',
            email='default@example.com',
            password='default'
        )
        logger.info(f'Created default user for MVP [EDITOR-VIEW01]')

    # Validate file path
    if not file_path.endswith('.md'):
        return render(request, 'editor/error.html', {
            'error': 'Only markdown files (.md) are supported'
        }, status=400)

    try:
        # Check for existing session
        existing_session = EditSession.get_user_session_for_file(user, file_path)

        if existing_session:
            # Resume existing session
            repo = get_repository()
            try:
                content = repo.get_file_content(file_path, existing_session.branch_name)
            except GitRepositoryError:
                content = ""

            logger.info(
                f'Resuming edit session {existing_session.id} for {file_path} '
                f'[EDITOR-VIEW02]'
            )

            return render(request, 'editor/edit.html', {
                'session_id': existing_session.id,
                'branch_name': existing_session.branch_name,
                'file_path': file_path,
                'content': content,
                'resumed': True
            })

        # Create new session via API internally
        repo = get_repository()
        branch_result = repo.create_draft_branch(user.id, user=user)
        branch_name = branch_result['branch_name']

        # Create edit session
        session = EditSession.objects.create(
            user=user,
            file_path=file_path,
            branch_name=branch_name,
            is_active=True
        )

        # Get current content
        try:
            content = repo.get_file_content(file_path, 'main')
        except GitRepositoryError:
            content = ""

        logger.info(
            f'Created edit session {session.id} for {file_path} on {branch_name} '
            f'[EDITOR-VIEW03]'
        )

        return render(request, 'editor/edit.html', {
            'session_id': session.id,
            'branch_name': branch_name,
            'file_path': file_path,
            'content': content,
            'resumed': False
        })

    except Exception as e:
        logger.error(f'Error loading editor page: {str(e)} [EDITOR-VIEW04]')
        return render(request, 'editor/error.html', {
            'error': f'Failed to load editor: {str(e)}'
        }, status=500)


def sessions_list(request):
    """
    List all active edit sessions for the current user.

    GET /editor/sessions/
    """
    # Get user (MVP: from query param)
    user_id = request.GET.get('user_id', '1')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return render(request, 'editor/error.html', {
            'error': 'User not found'
        }, status=404)

    sessions = EditSession.get_active_sessions(user=user)

    return render(request, 'editor/sessions.html', {
        'sessions': sessions,
        'user': user
    })
