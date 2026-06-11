from django.contrib import admin
from .models import AssignmentAuditLog, SystemAuditLog

@admin.register(AssignmentAuditLog)
class AssignmentAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'assignment', 'user', 'timestamp')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('action', 'assignment__title', 'user__username')
    readonly_fields = ('timestamp',)

@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_repr', 'ip_address')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__username', 'object_repr', 'details', 'ip_address')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
