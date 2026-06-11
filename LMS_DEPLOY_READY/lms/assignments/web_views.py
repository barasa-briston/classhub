from django.db import models
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .forms import AssignmentForm
from .models import Assignment, AssignmentAvailability
from approvals.models import AssignmentApproval
from audit.models import AssignmentAuditLog
from communications.models import Notice
from courses.models import Cohort


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
    from courses.models import Course, Module
    qs = AssignmentApproval.objects.filter(status="PENDING").select_related("assignment").order_by("assignment__sort_key")
    
    course_id = request.GET.get("course_id")
    module_id = request.GET.get("module_id")
    
    if course_id:
        qs = qs.filter(assignment__course_id=course_id)
    if module_id:
        qs = qs.filter(assignment__module_id=module_id)
        
    courses = Course.objects.all()
    modules = Module.objects.filter(course_id=course_id) if course_id else Module.objects.all()
        
    return render(request, "approvals/pending.html", {
        "items": qs,
        "courses": courses,
        "modules": modules,
        "selected_course": course_id,
        "selected_module": module_id
    })


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


@login_required
@user_passes_test(lambda u: is_lecturer(u) or is_admin(u))
def bulk_manage_assignments(request):
    user = request.user
    is_adm = is_admin(user)

    if is_adm:
        assignments = Assignment.objects.all().select_related('course', 'module').order_by('sort_key', 'created_at')
    else:
        # Lecturer: created by self OR in cohorts where they are a lecturer
        assignments = Assignment.objects.filter(
            models.Q(created_by=user) | 
            models.Q(availabilities__cohort__lecturers=user)
        ).distinct().select_related('course', 'module').order_by('sort_key', 'created_at')

    if request.method == "POST":
        assignment_ids = request.POST.getlist('selected_assignments')
        action = request.POST.get('action')

        if not assignment_ids:
            messages.warning(request, "No assignments selected.")
            return redirect('bulk-manage-assignments')

        selected_qs = assignments.filter(id__in=assignment_ids)
        count = 0

        if action == "set_deadline":
            deadline = request.POST.get('deadline')
            allow_late = request.POST.get('allow_late') == 'on'
            notify_users = request.POST.get('notify_users') == 'on'
            late_until = request.POST.get('late_until')
            late_penalty = request.POST.get('late_penalty', 0.0)

            if not deadline:
                messages.error(request, "Deadline is required for this action.")
                return redirect('bulk-manage-assignments')

            for assignment in selected_qs:
                availabilities = AssignmentAvailability.objects.filter(assignment=assignment)
                if not is_adm:
                    # Lecturers can only edit availabilities in their cohorts
                    availabilities = availabilities.filter(cohort__lecturers=user)

                for avail in availabilities:
                    old_deadline = avail.deadline
                    avail.deadline = deadline
                    avail.allow_late = allow_late
                    avail.late_until = late_until if allow_late else None
                    avail.late_penalty = late_penalty
                    avail.save()

                    # Audit Log
                    AssignmentAuditLog.objects.create(
                        user=user,
                        assignment=assignment,
                        action="Bulk Update Deadline",
                        details={
                            "cohort": avail.cohort.name,
                            "old_deadline": str(old_deadline),
                            "new_deadline": str(deadline),
                            "allow_late": allow_late,
                            "late_penalty": late_penalty
                        }
                    )

                    if notify_users:
                        # Notify Students
                        Notice.objects.create(
                            title=f"Deadline Updated: {assignment.title}",
                            content=f"The deadline for {assignment.title} (Cohort: {avail.cohort.name}) has been updated to {deadline}.",
                            cohort=avail.cohort,
                            author=user
                        )
                    count += 1

            messages.success(request, f"Updated deadline for {count} assignment availability records.")

        elif action == "update_visibility":
            status = request.POST.get('status')
            if status not in Assignment.Status.values:
                messages.error(request, "Invalid status selected.")
                return redirect('bulk-manage-assignments')

            for assignment in selected_qs:
                old_status = assignment.status
                assignment.status = status
                assignment.save()

                AssignmentAuditLog.objects.create(
                    user=user,
                    assignment=assignment,
                    action=f"Bulk Update Status to {status}",
                    details={"old_status": old_status, "new_status": status}
                )
                count += 1
            
            messages.success(request, f"Updated status to {status} for {count} assignments.")

        return redirect('bulk-manage-assignments')

    # Prefetch availabilities for display
    assignments = assignments.prefetch_related('availabilities__cohort')
    
    return render(request, "assignments/bulk_manage.html", {
        "assignments": assignments,
        "statuses": Assignment.Status.choices,
        "is_admin": is_adm,
    })
