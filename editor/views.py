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


def conflicts_list(request):
    """
    Display dashboard of all unresolved conflicts.

    GET /editor/conflicts/
    """
    from git_service.git_operations import get_repository

    try:
        repo = get_repository()
        conflicts_data = repo.get_conflicts()

        # Augment conflicts with EditSession information
        for conflict in conflicts_data['conflicts']:
            branch_name = conflict['branch_name']
            try:
                session = EditSession.objects.filter(
                    branch_name=branch_name,
                    is_active=True
                ).first()

                if session:
                    conflict['session'] = session
                    conflict['user_name'] = session.user.username if session.user else 'Unknown'
                    conflict['file_path'] = session.file_path
                else:
                    conflict['session'] = None
                    conflict['user_name'] = 'Unknown'
                    conflict['file_path'] = conflict['file_paths'][0] if conflict['file_paths'] else 'unknown'
            except Exception as e:
                logger.warning(f'Failed to get session for {branch_name}: {str(e)}')
                conflict['session'] = None
                conflict['user_name'] = 'Unknown'
                conflict['file_path'] = conflict['file_paths'][0] if conflict['file_paths'] else 'unknown'

        logger.info(f"Displayed conflicts dashboard with {len(conflicts_data['conflicts'])} conflicts [EDITOR-VIEW05]")

        return render(request, 'editor/conflicts.html', {
            'conflicts': conflicts_data['conflicts'],
            'cached': conflicts_data.get('cached', False),
            'timestamp': conflicts_data.get('timestamp'),
            'user': request.user
        })

    except Exception as e:
        messages.error(request, f'Error loading conflicts: {str(e)}')
        logger.error(f'Failed to load conflicts: {str(e)} [EDITOR-VIEW06]')
        return render(request, 'editor/conflicts.html', {
            'conflicts': [],
            'user': request.user
        })


def resolve_conflict_view(request, session_id, file_path):
    """
    Display conflict resolution interface.

    GET /editor/conflicts/resolve/<session_id>/<file_path>/
    """
    from git_service.git_operations import get_repository

    try:
        # Get edit session
        session = get_object_or_404(EditSession, id=session_id, is_active=True)

        # Check permission
        if request.user.is_authenticated and session.user != request.user:
            messages.error(request, 'You do not have permission to resolve this conflict.')
            return redirect('editor:conflicts-list')

        # Get three-way diff versions
        repo = get_repository()
        versions = repo.get_conflict_versions(session.branch_name, file_path)

        # Determine conflict type (text, image, or binary)
        conflict_type = 'text'  # default
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            conflict_type = 'image'
        elif not file_path.lower().endswith('.md'):
            conflict_type = 'binary'

        logger.info(f'Displaying conflict resolution for session {session_id}: {file_path} ({conflict_type}) [EDITOR-VIEW07]')

        # Choose appropriate template based on conflict type
        if conflict_type == 'image':
            template = 'editor/resolve_image_conflict.html'
        elif conflict_type == 'binary':
            template = 'editor/resolve_binary_conflict.html'
        else:
            template = 'editor/resolve_conflict.html'

        return render(request, template, {
            'session': session,
            'file_path': file_path,
            'versions': versions,
            'conflict_type': conflict_type,
            'user': request.user
        })

    except EditSession.DoesNotExist:
        messages.error(request, 'Edit session not found or inactive.')
        logger.error(f'Session not found: {session_id} [EDITOR-VIEW08]')
        return redirect('editor:conflicts-list')
    except Exception as e:
        messages.error(request, f'Error loading conflict resolution: {str(e)}')
        logger.error(f'Failed to load conflict resolution: {str(e)} [EDITOR-VIEW09]')
        return redirect('editor:conflicts-list')
