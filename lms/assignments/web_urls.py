from django.urls import path
from . import web_views

urlpatterns = [
    # lecturer
    path("lecturer/assignments/", web_views.lecturer_assignments, name="lecturer-assignments"),
    path("lecturer/assignments/create/", web_views.lecturer_create_assignment, name="lecturer-create-assignment"),

    # admin approvals (web page, not django admin)
    path("admin-panel/approvals/", web_views.admin_pending_approvals, name="admin-approvals"),
    path("admin-panel/approvals/<int:assignment_id>/reject/", web_views.admin_reject_assignment, name="admin-reject-assignment"),
]
