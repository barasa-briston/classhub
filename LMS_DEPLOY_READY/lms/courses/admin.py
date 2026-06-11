from django.contrib import admin
from .models import Cohort, Course, Enrollment, Module, Resource, FeePayment, OnlineMeeting, AttendanceRecord

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active", "created_at")
    list_editable = ("order", "is_active")
    search_fields = ("title", "description")

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "intake_label", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "intake_label")

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "cohort", "created_by")

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "order")
    list_filter = ("course",)
    search_fields = ("name",)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "certificate_lock_override", "manual_certificate", "enrolled_at")
    list_editable = ("certificate_lock_override",)
    search_fields = ("student__username", "student__first_name", "student__last_name", "course__name")

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'amount', 'transaction_id', 'status', 'payment_date')
    list_filter = ('status', 'course', 'payment_method', 'provider')
    search_fields = ('student__username', 'student__email', 'transaction_id', 'phone_number')
    readonly_fields = ('payment_date',)

@admin.register(OnlineMeeting)
class OnlineMeetingAdmin(admin.ModelAdmin):
    list_display = ('topic', 'cohort', 'meeting_date', 'duration_minutes')
    list_filter = ('cohort', 'meeting_date')
    search_fields = ('topic', 'meeting_link')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'student', 'joined_at', 'is_attended')
    list_filter = ('is_attended', 'meeting__cohort')
    search_fields = ('student__username', 'meeting__topic')
