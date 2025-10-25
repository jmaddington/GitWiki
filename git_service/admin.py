from django.contrib import admin
from django.utils.html import format_html
from .models import Configuration, GitOperation


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    """
    Enhanced Configuration admin interface.

    AIDEV-NOTE: config-admin; Categorized configuration management
    """
    list_display = ('key', 'value_display', 'category_badge', 'modified_at')
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'modified_at')
    list_filter = ('modified_at',)

    fieldsets = (
        ('Configuration', {
            'fields': ('key', 'value', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )

    def value_display(self, obj):
        """Display value with truncation for long values."""
        value_str = str(obj.value)
        if len(value_str) > 50:
            return f"{value_str[:47]}..."
        return value_str
    value_display.short_description = 'Value'

    def category_badge(self, obj):
        """Display category badge based on key prefix."""
        key = obj.key
        if key.startswith('github_') or key.startswith('webhook_'):
            color = '#0d6efd'  # Blue
            category = 'GitHub'
        elif key.startswith('permission_'):
            color = '#dc3545'  # Red
            category = 'Security'
        elif key.startswith('wiki_'):
            color = '#198754'  # Green
            category = 'Wiki'
        elif key.startswith('max_') or key.startswith('supported_'):
            color = '#ffc107'  # Yellow
            category = 'Uploads'
        elif key.startswith('branch_'):
            color = '#0dcaf0'  # Cyan
            category = 'Maintenance'
        else:
            color = '#6c757d'  # Gray
            category = 'Other'

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, category
        )
    category_badge.short_description = 'Category'
    category_badge.admin_order_field = 'key'


@admin.register(GitOperation)
class GitOperationAdmin(admin.ModelAdmin):
    """
    Enhanced GitOperation admin interface.

    AIDEV-NOTE: gitop-admin; Read-only audit log with statistics
    """
    list_display = ('timestamp', 'operation_type', 'user', 'branch_name', 'success_badge', 'execution_time_display')
    list_filter = ('operation_type', 'success', 'timestamp')
    search_fields = ('branch_name', 'file_path', 'error_message', 'user__username')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Operation Details', {
            'fields': ('operation_type', 'user', 'branch_name', 'file_path')
        }),
        ('Request/Response', {
            'fields': ('request_parameters', 'response_code', 'success')
        }),
        ('Output', {
            'fields': ('git_output', 'error_message', 'execution_time_ms')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )

    def success_badge(self, obj):
        """Display success/failure as colored badge."""
        if obj.success:
            return format_html(
                '<span style="background-color: #198754; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">✓ SUCCESS</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">✗ FAILED</span>'
            )
    success_badge.short_description = 'Status'
    success_badge.admin_order_field = 'success'

    def execution_time_display(self, obj):
        """Display execution time with color coding."""
        if obj.execution_time_ms is None:
            return '-'

        time_ms = obj.execution_time_ms

        # Color code based on execution time
        if time_ms < 100:
            color = '#198754'  # Green - fast
        elif time_ms < 1000:
            color = '#ffc107'  # Yellow - medium
        else:
            color = '#dc3545'  # Red - slow

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ms</span>',
            color, time_ms
        )
    execution_time_display.short_description = 'Execution Time'
    execution_time_display.admin_order_field = 'execution_time_ms'

    def has_add_permission(self, request):
        # Prevent manual creation of git operations
        return False

    def has_change_permission(self, request, obj=None):
        # Make git operations read-only
        return False
