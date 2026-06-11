from django.urls import path
from .views import (
    StudentSubmitAssignmentView,
    StudentMySubmissionsView,
    LecturerSubmissionsByAssignmentView,
    LecturerGradeSubmissionView,
    AdminUnlockSubmissionView
)

urlpatterns = [
    # student
    path("student/submit/", StudentSubmitAssignmentView.as_view()),
    path("student/mine/", StudentMySubmissionsView.as_view()),

    # lecturer
    path("lecturer/assignment/<int:assignment_id>/", LecturerSubmissionsByAssignmentView.as_view()),
    path("lecturer/grade/<int:submission_id>/", LecturerGradeSubmissionView.as_view()),

    # admin
    path("admin/unlock/<int:submission_id>/", AdminUnlockSubmissionView.as_view()),
]
