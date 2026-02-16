from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .forms import AssignmentForm
from .models import Assignment
from approvals.models import AssignmentApproval


def is_lecturer(user):
    return getattr(user, "role", "") == "LECTURER"

def is_admin(user):
    return user.is_superuser or getattr(user, "role", "") == "ADMIN"


@login_required
@user_passes_test(is_lecturer)
def lecturer_create_assignment(request):
    if request.method == "POST":
        form = AssignmentForm(request.POST)
        if form.is_valid():
            a = form.save(commit=False)
            a.created_by = request.user
            a.status = Assignment.Status.PENDING
            a.save()

            AssignmentApproval.objects.update_or_create(
                assignment=a,
                defaults={"requested_by": request.user, "status": "PENDING"},
            )

            messages.success(request, "Assignment sent for approval.")
            return redirect("lecturer-assignments")
    else:
        form = AssignmentForm()

    return render(request, "assignments/lecturer_create.html", {"form": form})


@login_required
@user_passes_test(is_lecturer)
def lecturer_assignments(request):
    qs = Assignment.objects.filter(created_by=request.user).order_by("-created_at")
    return render(request, "assignments/lecturer_list.html", {"assignments": qs})


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
    a.rejection_comment = ""
    a.save()

    AssignmentApproval.objects.update_or_create(
        assignment=a,
        defaults={"status": "APPROVED", "reviewed_by": request.user},
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
    a.approved_at = None
    a.save()

    AssignmentApproval.objects.update_or_create(
        assignment=a,
        defaults={"status": "REJECTED", "reviewed_by": request.user, "comment": comment},
    )

    messages.error(request, "Rejected ❌")
    return redirect("admin-approvals")

@login_required
@user_passes_test(is_admin)
def admin_approve_assignment(request, assignment_id):
    a = get_object_or_404(Assignment, id=assignment_id)

    a.status = Assignment.Status.APPROVED
    a.approved_by = request.user
    a.approved_at = timezone.now()
    a.rejection_comment = ""
    a.save()

    AssignmentApproval.objects.update_or_create(
        assignment=a,
        defaults={"status": "APPROVED", "reviewed_by": request.user, "comment": ""},
    )

    messages.success(request, "Approved ✅")
    return redirect("admin-approvals")

@login_required
@user_passes_test(is_lecturer)
def lecturer_approved_assignments(request):
    qs = Assignment.objects.filter(
        created_by=request.user,
        status=Assignment.Status.APPROVED
    ).order_by("-created_at")
    return render(request, "assignments/lecturer_list.html", {"assignments": qs})
