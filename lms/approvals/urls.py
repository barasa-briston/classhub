from django.urls import path
from . import web_views

urlpatterns = [
    path("approvals/", web_views.admin_pending_approvals, name="admin-approvals"),
    path("approvals/<int:assignment_id>/reject/", web_views.admin_reject_assignment, name="admin-reject-assignment"),
    path("approvals/<int:assignment_id>/approve/", web_views.admin_approve_assignment, name="admin-approve-assignment"),
]
