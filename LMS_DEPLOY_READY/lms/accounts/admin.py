from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile
from courses.models import Enrollment


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = "Student Profile Information"
    fk_name = "user"
    extra = 1 # Show on add page
    fields = ('registration_number', 'cohort', 'transcript_lock_override')
    readonly_fields = ('registration_number',)


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 1 # Show on add page
    verbose_name_plural = "Course Enrollments (Cohorts)"
    fields = ('course', 'cohort', 'certificate_lock_override', 'manual_certificate')
    # readonly_fields = ('get_cohort',) # Removed read-only helper


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [StudentProfileInline, EnrollmentInline]
    
    # Standard UserAdmin add_fieldsets
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("LMS Details", {"fields": ("role",)}),
    )

    fieldsets = (
        ("General", {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("Role & Access", {"fields": ("role", "groups", "user_permissions")}),
    )

    list_display = ("username", "email", "role", "is_staff", "is_active", "is_superuser")
    list_filter = ("role", "is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")

    def get_readonly_fields(self, request, obj=None):
        ro = []
        if not request.user.is_superuser:
            ro += ["is_superuser", "is_staff"]
        return ro

    def get_inline_instances(self, request, obj=None):
        # Force inlines to show on the ADD page in UserAdmin
        return super().get_inline_instances(request, obj)

# Unregister if registered elsewhere to avoid duplication
try:
    admin.site.unregister(StudentProfile)
except admin.sites.NotRegistered:
    pass
