"""
URL configuration for editor app.
"""

from django.urls import path
from .api import (
    StartEditAPIView,
    SaveDraftAPIView,
    CommitDraftAPIView,
    PublishEditAPIView,
    ValidateMarkdownAPIView,
    UploadImageAPIView,
    UploadFileAPIView,
    QuickUploadFileAPIView,
    ConflictsListAPIView,
    ConflictVersionsAPIView,
    ResolveConflictAPIView,
    DeleteFileAPIView
)
from . import views

app_name = 'editor'

urlpatterns = [
    # API endpoints
    path('api/start/', StartEditAPIView.as_view(), name='api-start-edit'),
    path('api/save/', SaveDraftAPIView.as_view(), name='api-save-draft'),
    path('api/commit/', CommitDraftAPIView.as_view(), name='api-commit-draft'),
    path('api/publish/', PublishEditAPIView.as_view(), name='api-publish-edit'),
    path('api/validate/', ValidateMarkdownAPIView.as_view(), name='api-validate-markdown'),
    path('api/upload-image/', UploadImageAPIView.as_view(), name='api-upload-image'),
    path('api/upload-file/', UploadFileAPIView.as_view(), name='api-upload-file'),
    path('api/quick-upload-file/', QuickUploadFileAPIView.as_view(), name='api-quick-upload-file'),
    path('api/delete-file/', DeleteFileAPIView.as_view(), name='api-delete-file'),

    # Conflict resolution API endpoints
    path('api/conflicts/', ConflictsListAPIView.as_view(), name='api-conflicts-list'),
    path('api/conflicts/versions/<int:session_id>/<path:file_path>/', ConflictVersionsAPIView.as_view(), name='api-conflict-versions'),
    path('api/conflicts/resolve/', ResolveConflictAPIView.as_view(), name='api-resolve-conflict'),

    # UI views
    path('edit/<path:file_path>/', views.edit_page, name='edit-page'),
    path('sessions/', views.list_sessions, name='list-sessions'),
    path('sessions/<int:session_id>/discard/', views.discard_session, name='discard-session'),

    # Conflict resolution UI views
    path('conflicts/', views.conflicts_list, name='conflicts-list'),
    path('conflicts/resolve/<int:session_id>/<path:file_path>/', views.resolve_conflict_view, name='resolve-conflict'),
]
