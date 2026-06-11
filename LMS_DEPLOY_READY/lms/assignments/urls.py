from django.urls import path
from .views import (
    LecturerCreateAssignmentView,
    LecturerMyAssignmentsView,
    AdminApproveAssignmentView,
    AdminRejectAssignmentView,
)

urlpatterns = [
    # lecturer
    path("lecturer/create/", LecturerCreateAssignmentView.as_view()),
    path("lecturer/mine/", LecturerMyAssignmentsView.as_view()),

    # admin approval
    path("admin/approve/<int:assignment_id>/", AdminApproveAssignmentView.as_view()),
    path("admin/reject/<int:assignment_id>/", AdminRejectAssignmentView.as_view()),
]
