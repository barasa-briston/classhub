from django.urls import path
from . import web_views

urlpatterns = [
    path("admin-panel/approvals/", web_views.admin_pending_approvals, name="admin-approvals"),
    path("admin-panel/approvals/<int:assignment_id>/approve/", web_views.admin_approve_assignment, name="admin-approve-assignment"),
    path("admin-panel/approvals/<int:assignment_id>/reject/", web_views.admin_reject_assignment, name="admin-reject-assignment"),
]
