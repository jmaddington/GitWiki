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
    UploadImageAPIView
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

    # UI views (to be implemented)
    path('edit/<path:file_path>/', views.edit_page, name='edit-page'),
    path('sessions/', views.list_sessions, name='list-sessions'),
    path('sessions/<int:session_id>/discard/', views.discard_session, name='discard-session'),
]
