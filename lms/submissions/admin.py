from django.contrib import admin
from .models import Submission, SubmissionFile


class SubmissionFileInline(admin.TabularInline):
    model = SubmissionFile
    extra = 0


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    inlines = [SubmissionFileInline]

    list_display = (
        "id",
        "student",
        "assignment",
        "submitted_at",
        "marks_awarded",
        "percentage",
        "grade",
        "is_marked",
        "is_approved",
    )

    list_filter = ("is_marked", "is_approved", "submitted_at")
    search_fields = ("student__username", "assignment__title")
    ordering = ("-submitted_at",)


@admin.register(SubmissionFile)
class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "original_name", "uploaded_at")
    search_fields = ("original_name", "submission__student__username", "submission__assignment__title")
    ordering = ("-uploaded_at",)

@admin.action(description="Approve selected submissions")
def approve_submissions(modeladmin, request, queryset):
    queryset.update(is_approved=True)

class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "assignment",
        "marks_awarded",
        "percentage",
        "grade",
        "is_marked",
        "is_approved",
    )
    list_filter = ("is_marked", "is_approved")
    actions = [approve_submissions]
