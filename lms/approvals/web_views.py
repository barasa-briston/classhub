from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from assignments.models import Assignment
from approvals.models import AssignmentApproval


def is_admin(user):
    return user.is_superuser or getattr(user, "role", "") in ["ADMIN"]


@login_required
@user_passes_test(is_admin)
def admin_pending_approvals(request):
    qs = AssignmentApproval.objects.filter(status="PENDING").select_related("assignment")
    return render(request, "approvals/pending.html", {"items": qs})


@login_required
@user_passes_test(is_admin)
def admin_approve_assignment(request, assignment_id):
    a = get_object_or_404(Assignment, id=assignment_id)

    a.status = Assignment.Status.APPROVED
    a.approved_by = request.user
    a.save()

    AssignmentApproval.objects.update_or_create(
        assignment=a,
        defaults={"status": "APPROVED", "reviewed_by": request.user}
    )

    messages.success(request, "Approved ✅")
    return redirect("admin-approvals")


@login_required
@user_passes_test(is_admin)
def admin_reject_assignment(request, assignment_id):
    a = get_object_or_404(Assignment, id=assignment_id)
    comment = request.POST.get("comment", "").strip()

    a.status = Assignment.Status.REJECTED
    a.rejection_comment = comment
    a.approved_by = None
    a.save()

    AssignmentApproval.objects.update_or_create(
        assignment=a,
        defaults={"status": "REJECTED", "reviewed_by": request.user, "comment": comment},
    )

    messages.error(request, "Rejected ❌")
    return redirect("admin-approvals")
