"""
URL configuration for Editor Service.

AIDEV-NOTE: editor-urls; Both API routes and HTML views for editor
"""

from django.urls import path
from .api import (
    StartEditAPIView,
    ValidateMarkdownAPIView,
    CommitDraftAPIView,
    PublishEditAPIView,
    UploadImageAPIView,
    DiscardDraftAPIView
)
from . import views

app_name = 'editor'

# API endpoints (used by AJAX in templates)
api_urlpatterns = [
    path('start/', StartEditAPIView.as_view(), name='api-start-edit'),
    path('validate/', ValidateMarkdownAPIView.as_view(), name='api-validate-markdown'),
    path('commit/', CommitDraftAPIView.as_view(), name='api-commit-draft'),
    path('publish/', PublishEditAPIView.as_view(), name='api-publish-edit'),
    path('upload-image/', UploadImageAPIView.as_view(), name='api-upload-image'),
    path('discard/', DiscardDraftAPIView.as_view(), name='api-discard-draft'),
]

# HTML views
view_urlpatterns = [
    path('sessions/', views.sessions_list, name='sessions-list'),
    path('<path:file_path>', views.edit_page, name='edit-page'),
]

urlpatterns = api_urlpatterns + view_urlpatterns
