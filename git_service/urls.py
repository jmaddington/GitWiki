"""
URL configuration for Git Service API.
"""

from django.urls import path
from .api import (
    CreateBranchAPIView,
    CommitChangesAPIView,
    PublishDraftAPIView,
    GetFileAPIView,
    ListBranchesAPIView
)
from . import views

app_name = 'git_service'

urlpatterns = [
    # API endpoints
    path('branch/create/', CreateBranchAPIView.as_view(), name='create-branch'),
    path('commit/', CommitChangesAPIView.as_view(), name='commit'),
    path('publish/', PublishDraftAPIView.as_view(), name='publish'),
    path('file/', GetFileAPIView.as_view(), name='get-file'),
    path('branches/', ListBranchesAPIView.as_view(), name='list-branches'),

    # Webhook endpoint
    path('webhook/', views.github_webhook_handler, name='webhook'),

    # Admin UI
    path('sync/', views.sync_management, name='sync-management'),
    path('settings/github/', views.github_settings, name='github-settings'),
]
