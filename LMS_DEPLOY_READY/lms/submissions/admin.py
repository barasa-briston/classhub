from django.contrib import admin
from .models import Submission, SubmissionFile

class SubmissionFileInline(admin.TabularInline):
    model = SubmissionFile
    extra = 0

@admin.action(description="Approve selected submissions")
def approve_submissions(modeladmin, request, queryset):
    queryset.update(is_approved=True)

@admin.action(description="Unlock selected submissions (Allow Resubmit)")
def unlock_submissions(modeladmin, request, queryset):
    rows_updated = queryset.update(is_locked=False)
    modeladmin.message_user(request, f"{rows_updated} submissions were successfully unlocked.")

@admin.action(description="Lock selected submissions (Finalize Grade)")
def lock_submissions(modeladmin, request, queryset):
    rows_updated = queryset.update(is_locked=True)
    modeladmin.message_user(request, f"{rows_updated} submissions were successfully locked.")

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    inlines = [SubmissionFileInline]
    list_display = (
        "id",
        "student",
        "assignment",
        "marks_awarded",
        "percentage",
        "grade",
        "is_marked",
        "is_approved",
        "is_locked",
        "submitted_at",
    )
    list_filter = ("is_marked", "is_approved", "is_locked", "submitted_at")
    search_fields = ("student__username", "assignment__title")
    ordering = ("-submitted_at",)
    actions = [approve_submissions, unlock_submissions, lock_submissions]

@admin.register(SubmissionFile)
class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "original_name", "uploaded_at")
    search_fields = ("original_name", "submission__student__username", "submission__assignment__title")
    ordering = ("-uploaded_at",)
