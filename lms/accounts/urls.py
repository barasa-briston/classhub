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
    path('password-reset-request/', views.request_password_reset, name='password-reset-request'),
    path('reset-confirm/<uuid:token>/', views.reset_confirm_view, name='password-reset-confirm'),
    path('manage-resets/', views.manage_password_resets, name='manage-password-resets'),
    path('fees/', views.view_fees, name='view-fees'),
    path('fee-statement/<int:course_id>/', views.download_fee_statement, name='download-fee-statement'),
    path('transcript/<int:course_id>/', views.download_transcript, name='download-transcript'),
    path('certificate/<int:course_id>/', views.download_certificate, name='download-certificate'),
    path('initiate-mpesa/', views.initiate_mpesa, name='initiate-mpesa'),
    path('submit-bank-payment/', views.submit_bank_payment, name='submit-bank-payment'),
    path('verify-payments/', views.verify_payments, name='verify-payments'),
    path('verify-payments/<int:payment_id>/', views.verify_payments, name='verify-payment'),
    path('reports/enrollment/', views.generate_enrollment_report, name='generate-enrollment-report'),
    path('reports/payment/', views.generate_payment_report, name='generate-payment-report'),

    # Meeting URLs
    path('meetings/manage/', courses_views.manage_meetings, name='manage-meetings'),
    path('meetings/upload-recording/<int:meeting_id>/', courses_views.upload_recording, name='upload-recording'),
    path('meetings/student/', courses_views.student_meetings, name='student-meetings'),
    path('track-attendance/<int:meeting_id>/', courses_views.track_attendance, name='track-attendance'),
    path('attendance-report/<int:cohort_id>/', courses_views.attendance_report, name='attendance-report'),
]
