from django.contrib import admin
from .models import Configuration, GitOperation


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description', 'modified_at')
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


@admin.register(GitOperation)
class GitOperationAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'operation_type', 'user', 'branch_name', 'success', 'execution_time_ms')
    list_filter = ('operation_type', 'success', 'timestamp')
    search_fields = ('branch_name', 'file_path', 'error_message')
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

    def has_add_permission(self, request):
        # Prevent manual creation of git operations
        return False

    def has_change_permission(self, request, obj=None):
        # Make git operations read-only
        return False
