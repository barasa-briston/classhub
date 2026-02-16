from django.contrib import admin
from .models import Cohort, Course, Enrollment

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "intake_label", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "intake_label")

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "cohort", "created_by")

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "enrolled_at")
