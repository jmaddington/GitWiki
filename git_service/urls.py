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

app_name = 'git_service'

urlpatterns = [
    path('branch/create/', CreateBranchAPIView.as_view(), name='create-branch'),
    path('commit/', CommitChangesAPIView.as_view(), name='commit'),
    path('publish/', PublishDraftAPIView.as_view(), name='publish'),
    path('file/', GetFileAPIView.as_view(), name='get-file'),
    path('branches/', ListBranchesAPIView.as_view(), name='list-branches'),
]
