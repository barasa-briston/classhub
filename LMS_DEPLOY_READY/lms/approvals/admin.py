from django.contrib import admin
from .models import AssignmentApproval

@admin.register(AssignmentApproval)
class AssignmentApprovalAdmin(admin.ModelAdmin):
    list_display = ("assignment", "status", "requested_by", "reviewed_by")
    list_filter = ("status",)
