"""
Views for Editor Service.

AIDEV-NOTE: editor-views; UI views for markdown editing
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import logging

from .models import EditSession
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def edit_page(request, file_path):
    """
    Display the markdown editor for a file.

    GET /editor/edit/<file_path>/
    """
    # For MVP, we'll use a default user if not authenticated
    # In production, this should require authentication based on permission_level
    user = request.user if request.user.is_authenticated else None

    context = {
        'file_path': file_path,
        'user': user or User.objects.get_or_create(id=1, defaults={'username': 'guest'})[0]
    }

    logger.info(f'Editing page: {file_path} [EDITOR-VIEW01]')

    return render(request, 'editor/edit.html', context)


def list_sessions(request):
    """
    List all active edit sessions for the current user.

    GET /editor/sessions/
    """
    # For MVP, show all sessions or filter by user if authenticated
    if request.user.is_authenticated:
        sessions = EditSession.get_active_sessions(user=request.user)
    else:
        # For demo purposes, show all active sessions
        sessions = EditSession.get_active_sessions()

    logger.info(f'Listing sessions: {sessions.count()} active [EDITOR-VIEW02]')

    return render(request, 'editor/sessions.html', {
        'sessions': sessions,
        'user': request.user
    })


def discard_session(request, session_id):
    """
    Discard an edit session.

    POST /editor/sessions/<session_id>/discard/
    """
    if request.method != 'POST':
        return redirect('editor:list-sessions')

    try:
        session = get_object_or_404(EditSession, id=session_id, is_active=True)

        # Check permission (user should own the session)
        if request.user.is_authenticated and session.user != request.user:
            messages.error(request, 'You do not have permission to discard this session.')
            return redirect('editor:list-sessions')

        # Mark session as inactive
        session.mark_inactive()

        messages.success(request, f'Draft session for {session.file_path} has been discarded.')
        logger.info(f'Discarded session {session_id} [EDITOR-VIEW03]')

    except Exception as e:
        messages.error(request, f'Error discarding session: {str(e)}')
        logger.error(f'Failed to discard session {session_id}: {str(e)} [EDITOR-VIEW04]')

    return redirect('editor:list-sessions')
