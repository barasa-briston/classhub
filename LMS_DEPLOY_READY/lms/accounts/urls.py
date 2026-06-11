from django.urls import path
from . import views
from courses import views as courses_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('dashboard/', views.dashboard_redirect, name='dashboard-redirect'),
    path('admin-panel/', views.admin_dashboard, name='admin-dashboard'),
    path('lecturer/', views.lecturer_dashboard, name='lecturer-dashboard'),
    path('student-directory/', views.lecturer_student_list, name='student-directory'),
    path('student-report/<int:student_id>/', views.student_submissions_report, name='view-student-report'),
    path('cohort-students/<int:cohort_id>/', views.cohort_student_submissions, name='cohort-students'),
    path('student/', views.student_dashboard, name='student-dashboard'),
    path('submit-assignment/<int:assignment_id>/', views.submit_assignment, name='submit-assignment'),
    path('grade-submission/<int:submission_id>/', views.grade_submission, name='grade-submission'),
    path('approve-assignment/<int:assignment_id>/', views.approve_assignment, name='approve-assignment'),
    path('reject-assignment/<int:assignment_id>/', views.reject_assignment, name='reject-assignment'),
    path('approve-grade/<int:submission_id>/', views.approve_grade, name='approve-grade'),
    path('manage-lecturers/', views.manage_lecturers, name='manage-lecturers'),
    path('manage-users/', views.manage_users, name='manage-users'),
    path('manage-cohorts/', views.manage_cohorts, name='manage-cohorts'),
    path('reject-submission/<int:submission_id>/', views.reject_submission, name='reject-submission'),
    path('create-assignment/', views.create_assignment, name='create-assignment'),
    path('delete-submission/<int:submission_id>/', views.delete_submission, name='delete-submission'),
    path('reset-submission/<int:submission_id>/', views.reset_submission, name='reset-submission'),
    path('password-reset-request/', views.request_password_reset, name='password-reset-request'),
    path('reset-confirm/<uuid:token>/', views.reset_confirm_view, name='password-reset-confirm'),
    path('manage-resets/', views.manage_password_resets, name='manage-password-resets'),
    path('fees/', views.view_fees, name='view-fees'),
    path('fee-structure/', views.download_fee_structure, name='download-fee-structure'),
    path('fee-statement/<int:course_id>/', views.download_fee_statement, name='download-fee-statement'),
    path('transcript/', views.download_transcript, name='download-transcript'),
    path('certificate/<int:course_id>/', views.download_certificate, name='download-certificate'),
    path('initiate-mpesa/', views.initiate_mpesa, name='initiate-mpesa'),
    path('submit-bank-payment/', views.submit_bank_payment, name='submit-bank-payment'),
    path('transfer-fee/', views.transfer_fee, name='transfer-fee'),
    path('verify-payments/', views.verify_payments, name='verify-payments'),
    path('verify-payments/<int:payment_id>/', views.verify_payments, name='verify-payment'),
    path('reports/enrollment/', views.generate_enrollment_report, name='generate-enrollment-report'),
    path('reports/payment/', views.generate_payment_report, name='generate-payment-report'),
    path('reports/fee-balance/', views.generate_fee_balance_report, name='generate-fee-balance-report'),
    path('reports/student-progress/', views.generate_student_progress_report, name='generate-student-progress-report'),

    # Meeting URLs
    path('meetings/manage/', courses_views.manage_meetings, name='manage-meetings'),
    path('meetings/delete/<int:meeting_id>/', courses_views.delete_meeting, name='delete-meeting'),
    path('meetings/edit/<int:meeting_id>/', courses_views.edit_meeting, name='edit-meeting'),
    path('meetings/upload-recording/<int:meeting_id>/', courses_views.upload_recording, name='upload-recording'),
    path('meetings/student/', courses_views.student_meetings, name='student-meetings'),
    path('track-attendance/<int:meeting_id>/', courses_views.track_attendance, name='track-attendance'),
    path('meeting-attendance/<int:meeting_id>/', courses_views.meeting_attendance_list, name='meeting-attendance-list'),
    path('attendance-report/<int:cohort_id>/', courses_views.attendance_report, name='attendance-report'),
    path('toggle-grade-lock/<int:submission_id>/', views.toggle_grade_lock, name='toggle-grade-lock'),

    # Resource Hub management (lecturer)
    path('resources/upload/', courses_views.upload_resource, name='upload-resource'),
    path('resources/delete/<int:resource_id>/', courses_views.delete_resource, name='delete-resource'),

    
    # Bulk Operations
    path('bulk-approve-assignments/', views.bulk_approve_assignments, name='bulk-approve-assignments'),
    path('bulk-reject-assignments/', views.bulk_reject_assignments, name='bulk-reject-assignments'),
    path('bulk-approve-grades/', views.bulk_approve_grades, name='bulk-approve-grades'),
]
