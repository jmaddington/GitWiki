from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import EditSession


@admin.register(EditSession)
class EditSessionAdmin(admin.ModelAdmin):
    """
    Enhanced EditSession admin interface.

    AIDEV-NOTE: editsess-admin; Session management with age indicators
    """
    list_display = ('user', 'file_path_display', 'branch_name', 'status_badge', 'session_age', 'last_modified')
    list_filter = ('is_active', 'created_at', 'last_modified', 'user')
    search_fields = ('user__username', 'file_path', 'branch_name')
    readonly_fields = ('created_at', 'last_modified', 'session_age')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Session Details', {
            'fields': ('user', 'file_path', 'branch_name', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_modified', 'session_age')
        }),
    )

    actions = ['mark_sessions_inactive', 'delete_inactive_sessions']

    def file_path_display(self, obj):
        """Display file path with truncation."""
        path = obj.file_path
        if len(path) > 50:
            return f"...{path[-47:]}"
        return path
    file_path_display.short_description = 'File Path'
    file_path_display.admin_order_field = 'file_path'

    def status_badge(self, obj):
        """Display active/inactive status as badge."""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #198754; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">ACTIVE</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">INACTIVE</span>'
            )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'is_active'

    def session_age(self, obj):
        """Calculate and display session age with color coding."""
        now = timezone.now()
        age = now - obj.created_at

        # Format age display
        if age < timedelta(hours=1):
            age_str = f"{int(age.total_seconds() / 60)} minutes"
            color = '#198754'  # Green - recent
        elif age < timedelta(days=1):
            age_str = f"{int(age.total_seconds() / 3600)} hours"
            color = '#ffc107'  # Yellow - today
        elif age < timedelta(days=7):
            age_str = f"{age.days} days"
            color = '#fd7e14'  # Orange - this week
        else:
            age_str = f"{age.days} days"
            color = '#dc3545'  # Red - old

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, age_str
        )
    session_age.short_description = 'Age'

    def mark_sessions_inactive(self, request, queryset):
        """Admin action to mark selected sessions as inactive."""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} session(s) marked as inactive.')
    mark_sessions_inactive.short_description = "Mark selected sessions as inactive"

    def delete_inactive_sessions(self, request, queryset):
        """Admin action to delete inactive sessions."""
        inactive = queryset.filter(is_active=False)
        count = inactive.count()
        inactive.delete()
        self.message_user(request, f'{count} inactive session(s) deleted.')
    delete_inactive_sessions.short_description = "Delete inactive sessions"
