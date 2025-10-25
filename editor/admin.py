from django.contrib import admin
from .models import EditSession


@admin.register(EditSession)
class EditSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'file_path', 'branch_name', 'is_active', 'last_modified', 'created_at')
    list_filter = ('is_active', 'created_at', 'last_modified')
    search_fields = ('user__username', 'file_path', 'branch_name')
    readonly_fields = ('created_at', 'last_modified')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Session Details', {
            'fields': ('user', 'file_path', 'branch_name', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_modified')
        }),
    )

    actions = ['mark_sessions_inactive']

    def mark_sessions_inactive(self, request, queryset):
        """Admin action to mark selected sessions as inactive."""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} session(s) marked as inactive.')
    mark_sessions_inactive.short_description = "Mark selected sessions as inactive"
