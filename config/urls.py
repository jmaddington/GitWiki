"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from config.health import health_check, readiness_check, liveness_check

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication URLs (must come before catch-all patterns)
    # AIDEV-NOTE: auth-urls; Django built-in authentication views
    path("accounts/login/", auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name='logout'),
    # Health check endpoints
    # AIDEV-NOTE: health-endpoints; Monitoring endpoints for load balancers and orchestration
    path("health/", health_check, name='health-check'),
    path("ready/", readiness_check, name='readiness-check'),
    path("alive/", liveness_check, name='liveness-check'),
    # API and app URLs
    path("api/git/", include('git_service.urls')),
    path("editor/", include('editor.urls')),
    path("wiki/", include('display.urls')),  # Wiki pages
    path("", include('display.urls')),  # Home page at root (catch-all, must be last)
]

# Error Handlers
# AIDEV-NOTE: error-handlers; Custom error pages for production
handler404 = 'display.views.custom_404'
handler500 = 'display.views.custom_500'
handler403 = 'display.views.custom_403'
