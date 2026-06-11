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
    a.save()

    AssignmentApproval.objects.update_or_create(
        assignment=a,
        defaults={"status": "APPROVED", "reviewed_by": request.user}
    )

    # Notify Lecturer
    from django.core.mail import send_mail
    from django.conf import settings
    if a.created_by and a.created_by.email:
        subject = f"Assignment Approved: {a.title}"
        message = f"Dear {a.created_by.username},\n\nYour assignment '{a.title}' has been approved by the Admin and is now available to students."
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [a.created_by.email], fail_silently=False)

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

    # Notify Lecturer
    from django.core.mail import send_mail
    from django.conf import settings
    if a.created_by and a.created_by.email:
        subject = f"Assignment Rejected: {a.title}"
        message = f"Dear {a.created_by.username},\n\nYour assignment '{a.title}' has been rejected by the Admin.\nReason: {comment}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [a.created_by.email], fail_silently=False)

    messages.error(request, "Rejected ❌")
    return redirect("admin-approvals")
