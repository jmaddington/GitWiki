"""
URL routing for display service.

AIDEV-NOTE: display-urls; Wiki page URLs and search routing
"""

from django.urls import path
from . import views

app_name = 'display'

urlpatterns = [
    # Home page
    path('', views.wiki_home, name='home'),

    # New page creation
    path('new/', views.new_page, name='new-page'),

    # New folder creation
    path('new-folder/', views.new_folder, name='new-folder'),

    # Search
    path('search/', views.wiki_search, name='search'),

    # Page history
    path('history/<path:file_path>/', views.page_history, name='history'),

    # Wiki pages (catch-all, must be last)
    path('<path:file_path>/', views.wiki_page, name='page'),
]
