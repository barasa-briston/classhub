from django.contrib import admin
from .models import Assignment

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "status", "deadline", "created_by")
    list_filter = ("status", "course")
    search_fields = ("title",)
