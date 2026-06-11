from django.contrib import admin
from .models import Assignment, AssignmentAvailability

@admin.register(AssignmentAvailability)
class AssignmentAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("assignment", "cohort", "deadline", "allow_late")
    list_filter = ("cohort", "assignment__course")
    search_fields = ("assignment__title", "cohort__name")
    ordering = ("assignment__sort_key",)

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "status", "is_exam", "created_by")
    list_filter = ("status", "course", "is_exam")
    search_fields = ("title",)
    ordering = ("sort_key",)
