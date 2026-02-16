from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

from assignments.models import Assignment
from submissions.models import Submission
from courses.models import Cohort, Course, FeePayment, Enrollment, OnlineMeeting, AttendanceRecord
from django.contrib.auth import get_user_model, logout
from .models import PasswordResetRequest
from django.db.models import Sum, Q
import datetime

User = get_user_model()
# Grade is not currently used as a separate model in assignments/submissions in the same way, 
# so we might need to adjust student_dashboard query.

# Handle logout
@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard_redirect(request):
    # Redirect based on the user's role or superuser status
    if request.user.is_superuser or request.user.role in ['ADMIN', 'SUPERADMIN']:
        return redirect("admin-dashboard")
    elif request.user.role == 'LECTURER':
        return redirect("lecturer-dashboard")
    elif request.user.role == 'STUDENT':
        return redirect("student-dashboard")
    
    # If role is not recognized but user is logged in, perhaps default to a fallback or 404
    raise Http404("You are not authorized to access this page.")

# Admin Dashboard
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404("You are not authorized to view this page.")
    
    # Assignments needing approval
    pending_assignments = Assignment.objects.filter(status='PENDING')
    # Grades (marked submissions) needing approval
    pending_grades = Submission.objects.filter(is_marked=True, is_approved=False)
    # Payments needing verification
    pending_payments_count = FeePayment.objects.filter(status='PENDING').count()
    
    assignments = Assignment.objects.all()
    submissions = Submission.objects.all()
    
    # --- Student Performance Section ---
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # 1. Base Query
    students_query = User.objects.filter(role='STUDENT').prefetch_related(
        'submissions', 
        'submissions__assignment'
    ).order_by('username')
    
    # 2. Search
    search_query = request.GET.get('q', '')
    if search_query:
        students_query = students_query.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query)
        )

    # 3. Pagination
    per_page = request.GET.get('per_page', '10')
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 30, 50, 100, 150]:
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(students_query, per_page)
    page_number = request.GET.get('page')
    students_page = paginator.get_page(page_number)
    
    # Prepare pagination options for template to avoid syntax errors
    per_page_options = []
    for pp in [10, 20, 30, 50, 100, 150]:
        per_page_options.append({
            'value': pp,
            'selected': 'selected' if pp == per_page else ''
        })

    return render(request, 'admin_dashboard.html', {
        'assignments': assignments,
        'submissions': submissions,
        'students': students_page, # Pass the page object, not the full queryset
        'search_query': search_query,
        'per_page': str(per_page),
        'per_page_options': per_page_options,
        'pending_assignments': pending_assignments,
        'pending_grades': pending_grades,
        'pending_payments_count': pending_payments_count,
    })

# Lecturer Dashboard
@login_required
def lecturer_dashboard(request):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to view this page.")
    
    # Lecturers only see assignments in cohorts they are assigned to
    from courses.models import Cohort
    assigned_cohorts = Cohort.objects.filter(lecturers=request.user)
    assignments = Assignment.objects.filter(course__cohort__in=assigned_cohorts)
    
    # Also show submissions for these assignments that need marking
    pending_submissions = Submission.objects.filter(assignment__in=assignments, is_marked=False)
    marked_submissions = Submission.objects.filter(assignment__in=assignments, is_marked=True)

    return render(request, 'lecturer_dashboard.html', {
        'cohorts': assigned_cohorts,
        'assignments': assignments,
        'pending_submissions': pending_submissions,
        'marked_submissions': marked_submissions,
    })

# Student Dashboard
@login_required
def student_dashboard(request):
    if not request.user.is_superuser and request.user.role != 'STUDENT':
        raise Http404("You are not authorized to view this page.")
    
    from courses.models import Enrollment
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__cohort')
    
    # Strictly check if student has any active cohorts
    # If all cohorts are over, we might want to restrict access or show a warning
    all_over = all(e.course.cohort.is_study_period_over for e in enrollments) if enrollments.exists() else False
    
    # Calculate stats
    submissions = Submission.objects.filter(student=request.user).select_related('assignment', 'assignment__course')
    graded_submissions = submissions.filter(is_marked=True)
    
    avg_mark = 0
    if graded_submissions.exists():
        from django.db.models import Avg
        avg_mark = graded_submissions.aggregate(Avg('percentage'))['percentage__avg'] or 0
        
        # Reward: Perfect Attendance adds a bonus (e.g. 5% boost to average, capped at 100)
        # We need to check attendance for ALL enrollments
        perfect_attendance = True
        has_meetings = False
        for enrollment in enrollments:
            cohort = enrollment.course.cohort
            total = OnlineMeeting.objects.filter(cohort=cohort).count()
            if total > 0:
                has_meetings = True
                attended = AttendanceRecord.objects.filter(student=request.user, meeting__cohort=cohort, is_attended=True).count()
                if attended < total:
                    perfect_attendance = False
                    break
            else:
                # If no meetings yet, we can't say they have perfect attendance for that cohort?
                # Or maybe we only count cohorts that have meetings.
                pass
        
        if has_meetings and perfect_attendance:
            avg_mark = min(100, avg_mark + 5) # 5% bonus for perfect attendance

    pass_status = "PENDING"
    if graded_submissions.exists():
        pass_status = "PASS" if avg_mark >= 50 else "FAIL"

    submitted_ids = submissions.values_list('assignment_id', flat=True)
    from assignments.models import Assignment
    available_assignments = Assignment.objects.filter(
        course__in=[e.course for e in enrollments], 
        status='APPROVED'
    ).exclude(id__in=submitted_ids)

    # Attendance stats
    attendance_data = []
    for enrollment in enrollments:
        cohort = enrollment.course.cohort
        # Only count meetings that have already occurred or are current
        total_meetings = OnlineMeeting.objects.filter(
            cohort=cohort,
            meeting_date__lte=timezone.now()
        ).count()
        
        attended_count = AttendanceRecord.objects.filter(
            student=request.user, 
            meeting__cohort=cohort,
            is_attended=True
        ).count()
        
        # Detect active meeting for this enrollment
        active_meeting = OnlineMeeting.objects.filter(cohort=cohort).order_by('-meeting_date').first()
        is_live = active_meeting.is_active if active_meeting else False
        
        percentage = (attended_count / total_meetings * 100) if total_meetings > 0 else 0
        attendance_data.append({
            'course_id': enrollment.course.id,
            'percentage': round(percentage, 1),
            'perfect': attended_count == total_meetings and total_meetings > 0,
            'active_meeting': active_meeting if is_live else None
        })
    
    return render(request, 'student_dashboard.html', {
        'submissions': submissions,
        'available_assignments': available_assignments,
        'enrollments': enrollments,
        'avg_mark': round(avg_mark, 2),
        'pass_status': pass_status,
        'all_over': all_over,
        'attendance_data': attendance_data
    })

from .forms import PasswordResetConfirmForm
from django.contrib.auth.hashers import make_password

def request_password_reset(request):
    from .forms import PasswordResetRequestForm
    from django.contrib.auth.hashers import make_password

    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            new_password = form.cleaned_data['new_password']
            
            # Check for existing pending request
            existing = PasswordResetRequest.objects.filter(user=user, status='PENDING').first()
            if existing:
                existing.new_password_hash = make_password(new_password)
                existing.is_verified = True
                existing.save()
                messages.success(request, f"Your previous request for '{user.username}' has been updated and is pending Admin approval.")
            else:
                PasswordResetRequest.objects.create(
                    user=user,
                    new_password_hash=make_password(new_password),
                    is_verified=True
                )
                
                # Notify Admins
                from django.core.mail import send_mail
                from django.conf import settings
                from django.db.models import Q
                
                admins = User.objects.filter(Q(role='ADMIN') | Q(is_superuser=True)).distinct()
                admin_emails = [a.email for a in admins if a.email]
                
                if admin_emails:
                    subject_admin = f"New Password Reset Request: {user.username}"
                    message_admin = f"A new password reset request has been submitted by {user.username}.\nPlease log in to the Admin Dashboard to approve or reject this request."
                    send_mail(subject_admin, message_admin, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=True)

                messages.success(request, "Your password reset request has been submitted and is pending Admin approval.")
            
            if request.user.is_authenticated:
                return redirect('dashboard-redirect')
            return redirect('login')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['username'] = request.user.username
        form = PasswordResetRequestForm(initial=initial)
            
    return render(request, 'accounts/password_reset_request.html', {'form': form})

def reset_confirm_view(request, token):
    reset_req = get_object_or_404(PasswordResetRequest, token=token, status='PENDING')
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(reset_req.user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            reset_req.new_password_hash = make_password(new_password)
            reset_req.is_verified = True
            reset_req.save()
            messages.success(request, "Your password change is confirmed and awaiting Admin approval.")
            return redirect('login')
    else:
        form = PasswordResetConfirmForm(reset_req.user)
    
    return render(request, 'accounts/reset_confirm.html', {'form': form, 'token': token})

@login_required
def manage_password_resets(request):
    if not request.user.is_superuser and request.user.role != 'ADMIN':
        raise Http404()
    
    # verified_requests: User has clicked link and submitted new password. Admin can Approve/Reject.
    verified_requests = PasswordResetRequest.objects.filter(status='PENDING', is_verified=True).order_by('-requested_at')
    
    # unverified_requests: User requested but hasn't clicked link/submitted form yet.
    unverified_requests = PasswordResetRequest.objects.filter(status='PENDING', is_verified=False).order_by('-requested_at')
    
    if request.method == "POST":
        req_id = request.POST.get('request_id')
        action = request.POST.get('action') # approve or reject
        reset_req = get_object_or_404(PasswordResetRequest, id=req_id)
        
        from django.utils import timezone
        reset_req.approved_by = request.user
        reset_req.approved_at = timezone.now()
        
        if action == 'approve':
            reset_req.status = 'APPROVED'
            if reset_req.new_password_hash:
                user = reset_req.user
                user.password = reset_req.new_password_hash
                user.save()
                messages.success(request, f"Approved and applied new password for {reset_req.user.username}.")
            else:
                messages.error(request, "Error: No new password found for this request.")
        else:
            reset_req.status = 'REJECTED'
            reset_req.admin_comment = request.POST.get('comment', '')
            messages.warning(request, f"Rejected reset for {reset_req.user.username}.")
        
        reset_req.save()
        return redirect('manage-password-resets')

    return render(request, 'accounts/manage_resets.html', {
        'verified_requests': verified_requests,
        'unverified_requests': unverified_requests
    })

# Submission Handling (Students)
@login_required
def submit_assignment(request, assignment_id):
    if not request.user.is_superuser and request.user.role != 'STUDENT':
        raise Http404("You are not authorized to submit this assignment.")
    
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    if request.method == 'POST':
        submission_files = request.FILES.getlist('submission_files')
        if not submission_files:
            messages.error(request, "Please upload at least one file.")
            return redirect('submit-assignment', assignment_id=assignment_id)

        # Handle potential resubmission
        submission, created = Submission.objects.get_or_create(student=request.user, assignment=assignment)
        
        if not created and submission.is_locked:
            messages.error(request, "This assignment is locked and cannot be resubmitted.")
            return redirect('student-dashboard')
            
        # Update timestamp for resubmissions
        if not created:
            from django.utils import timezone
            submission.submitted_at = timezone.now()
            # Optional: Reset grading status if allowing resubmission
            submission.is_marked = False
            submission.grade = ""
            submission.percentage = None
        
        submission.save()
        
        from submissions.models import SubmissionFile
        for file in submission_files:
            SubmissionFile.objects.create(
                submission=submission, 
                file=file,
                original_name=file.name
            )
            
        messages.success(request, f"Assignment '{assignment.title}' submitted successfully!")
        return redirect('student-dashboard')
    
    return render(request, 'submit_assignment.html', {'assignment': assignment})

# Grading Handling (Lecturers)
@login_required
def grade_submission(request, submission_id):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to grade this submission.")
    
    submission = get_object_or_404(Submission, id=submission_id)
    
    # Check if this lecturer is assigned to the cohort this student is in
    from courses.models import Cohort
    if not request.user.is_superuser:
        is_assigned = Cohort.objects.filter(lecturers=request.user, courses__assignments__submissions=submission).exists()
        if not is_assigned:
            raise Http404("You are not authorized to grade this submission (Cohort mismatch).")

    # Check if grade is locked
    if submission.is_locked:
        messages.warning(request, "This grade is locked and cannot be edited.")
        return redirect('lecturer-dashboard')

    if request.method == 'POST':
        try:
            marks = float(request.POST.get('marks', 0))
            feedback = request.POST.get('feedback', '')
            submission.marks_awarded = marks
            submission.feedback = feedback
            # submission.save() will handle percentage and grade locking logic
            submission.save()
            messages.success(request, f"Marked {submission.student.username}'s submission.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid marks provided.")
        return redirect('lecturer-dashboard')
    return render(request, 'grade_submission.html', {'submission': submission})

# Assignment Creation (Lecturers)
from assignments.forms import AssignmentForm
@login_required
def create_assignment(request):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to create assignments.")
    
    from courses.models import Course, Cohort
    assigned_cohorts = Cohort.objects.filter(lecturers=request.user)
    available_courses = Course.objects.filter(cohort__in=assigned_cohorts)

    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.created_by = request.user
            assignment.status = 'PENDING'
            # Ensure the selected course is actually assigned to the lecturer
            if not request.user.is_superuser and assignment.course not in available_courses:
                 messages.error(request, "Invalid course selected.")
            else:
                assignment.save()
                messages.success(request, "Assignment created and pending approval.")
                return redirect('lecturer-dashboard')
    else:
        form = AssignmentForm()
        # Filter courses in the form
        if not request.user.is_superuser:
            form.fields['course'].queryset = available_courses
            
    return render(request, 'create_assignment.html', {'form': form})

# Admin Approval Actions
@login_required
@require_POST
def approve_assignment(request, assignment_id):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return redirect('home')
    assignment = get_object_or_404(Assignment, id=assignment_id)
    assignment.status = 'APPROVED'
    assignment.approved_by = request.user
    from django.utils import timezone
    assignment.approved_at = timezone.now()
    assignment.save()
    messages.success(request, f"Assignment '{assignment.title}' approved.")
    return redirect('admin-dashboard')

@login_required
@require_POST
def reject_assignment(request, assignment_id):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return redirect('home')
    
    assignment = get_object_or_404(Assignment, id=assignment_id)
    reason = request.POST.get('rejection_reason', '').strip()
    
    if not reason:
        messages.error(request, "A reason is required to reject an assignment.")
        return redirect('admin-dashboard')

    assignment.status = 'REJECTED' # Or 'DRAFT' if you want them to edit it immediately, but REJECTED is clearer status
    # If we want the lecturer to edit it, we might set it to DRAFT? 
    # The requirement says "provide a reason... proper feedback". 
    # Usually REJECTED status is fine, and lecturer can see it and edit it back to PENDING.
    
    assignment.rejection_comment = reason
    assignment.approved_by = None
    assignment.approved_at = None
    assignment.save()
    
    messages.warning(request, f"Assignment '{assignment.title}' rejected.")
    return redirect('admin-dashboard')

@login_required
@require_POST
def approve_grade(request, submission_id):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return redirect('home')
    submission = Submission.objects.get(id=submission_id)
    submission.is_approved = True
    submission.is_locked = True # Lock grade once approved
    submission.approved_by = request.user
    import django.utils.timezone as timezone
    submission.approved_at = timezone.now()
    submission.save()
    return redirect('admin-dashboard')

@login_required
@require_POST
def reject_submission(request, submission_id):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return redirect('home')
    
    submission = Submission.objects.get(id=submission_id)
    feedback = request.POST.get('feedback', 'Rejected by Admin.')
    
    submission.is_approved = False
    submission.is_marked = False # Allow re-marking/resubmitting
    submission.is_locked = False
    submission.feedback = feedback
    # We could add an actual status field, but for now we follow the existing boolean logic
    submission.save()
    messages.warning(request, f"Rejected submission from {submission.student.username}")
    return redirect('admin-dashboard')
@login_required
def manage_lecturers(request):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404("You are not authorized to view this page.")
    
    lecturers = User.objects.filter(role='LECTURER')
    cohorts = Cohort.objects.all()
    
    if request.method == 'POST':
        lecturer_id = request.POST.get('lecturer_id')
        cohort_id = request.POST.get('cohort_id')
        action = request.POST.get('action') # 'assign' or 'unassign'
        
        lecturer = get_object_or_404(User, id=lecturer_id, role='LECTURER')
        cohort = get_object_or_404(Cohort, id=cohort_id)
        
        if action == 'assign':
            cohort.lecturers.add(lecturer)
            messages.success(request, f"Assigned {lecturer.username} to {cohort.name}")
        elif action == 'unassign':
            cohort.lecturers.remove(lecturer)
            messages.success(request, f"Removed {lecturer.username} from {cohort.name}")
            
        return redirect('manage-lecturers')

    return render(request, 'manage_lecturers.html', {
        'lecturers': lecturers,
        'cohorts': cohorts,
    })

@login_required
def manage_users(request):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404("You are not authorized to view this page.")
    
    users = User.objects.all().order_by('role', 'username')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'delete':
            user_to_delete = get_object_or_404(User, id=user_id)
            if user_to_delete.is_superuser:
                 messages.error(request, "Cannot delete a Superuser.")
            else:
                username = user_to_delete.username
                user_to_delete.delete()
                messages.success(request, f"User {username} deleted successfully.")
        
        elif action == 'update_role':
            user_to_update = get_object_or_404(User, id=user_id)
            new_role = request.POST.get('role')
            if new_role in dict(User._meta.get_field('role').choices):
                user_to_update.role = new_role
                user_to_update.save()
                messages.success(request, f"Updated {user_to_update.username}'s role to {new_role}")
            
        return redirect('manage-users')

    if request.method == 'POST' and 'create_user' in request.POST:
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'STUDENT')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            new_user = User.objects.create_user(username=username, email=email, password=password)
            new_user.role = role
            new_user.save()
            messages.success(request, f"User {username} created as {role}!")
            return redirect('manage-users')

    return render(request, 'manage_users.html', {'users_list': users})

@login_required
def manage_cohorts(request):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404("You are not authorized to view this page.")
    
    cohorts = Cohort.objects.all().order_by('-start_date')
    
    if request.method == 'POST':
        cohort_id = request.POST.get('cohort_id')
        cohort = get_object_or_404(Cohort, id=cohort_id)
        
        cohort.start_date = request.POST.get('start_date') or None
        cohort.end_date = request.POST.get('end_date') or None
        cohort.is_active = 'is_active' in request.POST
        cohort.save()
        
        messages.success(request, f"Updated cohort {cohort.name} successfully.")
        return redirect('manage-cohorts')

    return render(request, 'manage_cohorts.html', {'cohorts': cohorts})

# --- PDF Generation Helper ---
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

# --- New Features for Student Portal ---

@login_required
def view_fees(request):
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can view fees.")
    
    enrollments = Enrollment.objects.filter(student=request.user)
    fee_data = []
    
    for enrollment in enrollments:
        course = enrollment.course
        payments = FeePayment.objects.filter(student=request.user, course=course).order_by('-payment_date')
        # Only count approved (and pending) payments towards the total paid. Exclude rejected.
        # This ensures that if a payment is rejected, the balance "increases" (reverts).
        valid_payments = payments.exclude(status='REJECTED')
        total_paid = valid_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        balance = course.fee - total_paid
        
        fee_data.append({
            'course': course,
            'payments': payments,
            'total_paid': total_paid,
            'balance': balance
        })
        
    return render(request, 'student_fees.html', {'fee_data': fee_data})

@login_required
def download_fee_statement(request, course_id):
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can download fee statements.")
        
    course = get_object_or_404(Course, id=course_id)
    # Ensure enrollment
    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        raise Http404("You are not enrolled in this course.")
        
    payments = FeePayment.objects.filter(student=request.user, course=course, status='APPROVED').order_by('payment_date')
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = course.fee - total_paid
    
    context = {
        'student': request.user,
        'course': course,
        'payments': payments,
        'total_paid': total_paid,
        'balance': balance,
        'date': datetime.date.today(),
    }
    
    # We need to use the render_to_pdf from utils.reports
    from utils.reports import render_to_pdf
    
    filename = f"Fee_Statement_{request.user.username}_{course.id}.pdf"
    return render_to_pdf('pdf/fee_statement.html', context, filename=filename)

@login_required
def download_transcript(request, course_id):
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can download transcripts.")
        
    course = get_object_or_404(Course, id=course_id)
    # Ensure student is enrolled
    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        raise Http404("You are not enrolled in this course.")
        
    # Gather Data
    submissions = Submission.objects.filter(
        student=request.user, 
        assignment__course=course,
        is_marked=True
    ).select_related('assignment')
    
    from django.db.models import Avg
    avg_mark = submissions.aggregate(Avg('percentage'))['percentage__avg'] or 0
    pass_status = "PASS" if avg_mark >= 50 else "FAIL"
    
    context = {
        'student': request.user,
        'course': course,
        'submissions': submissions,
        'avg_mark': avg_mark,
        'pass_status': pass_status,
    }
    
    pdf = render_to_pdf('pdf/transcript.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Transcript_{request.user.username}_{course.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)

@login_required
def download_certificate(request, course_id):
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can download certificates.")
        
    course = get_object_or_404(Course, id=course_id)
    if not Enrollment.objects.filter(student=request.user, course=course).exists():
         raise Http404("You are not enrolled.")
         
    # Check if course is completed? 
    # For now, let's assume they can download if they have passed or if the cohort is over.
    # Or maybe strictly check pass status.
    
    submissions = Submission.objects.filter(
        student=request.user, 
        assignment__course=course, 
        is_marked=True
    )
    
    # Simple check: calculate average
    from django.db.models import Avg
    avg_mark = submissions.aggregate(Avg('percentage'))['percentage__avg'] or 0
    
    if avg_mark < 50:
        messages.error(request, "You have not passed the course yet.")
        return redirect('student-dashboard')
        
    context = {
        'student': request.user,
        'course': course,
    }
    
    pdf = render_to_pdf('pdf/certificate.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Certificate_{request.user.username}_{course.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)

@login_required
@require_POST
def initiate_mpesa(request):
    if request.user.role != 'STUDENT':
        raise Http404()
        
    course_id = request.POST.get('course_id')
    amount = request.POST.get('amount')
    phone = request.POST.get('phone_number')
    transaction_id = request.POST.get('transaction_id')
    provider = request.POST.get('provider', 'M-Pesa') # Default to M-Pesa if not set
    
    if not all([course_id, amount, phone, transaction_id]):
        messages.error(request, "All fields are required.")
        return redirect('view-fees')

    course = get_object_or_404(Course, id=course_id)
    
    try:
        FeePayment.objects.create(
            student=request.user,
            course=course,
            amount=amount,
            payment_method='Mobile Money', # Changed from 'M-Pesa'
            provider=provider,
            transaction_id=transaction_id.upper(), # Ensure uppercase
            phone_number=phone,
            status='PENDING' # Now requires admin approval
        )
        messages.success(request, f"M-Pesa payment {transaction_id} submitted for verification.")
    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
    
    return redirect('view-fees')

@login_required
@require_POST
def submit_bank_payment(request):
    if request.user.role != 'STUDENT':
        raise Http404()
        
    course_id = request.POST.get('course_id')
    amount = request.POST.get('amount')
    transaction_id = request.POST.get('transaction_id')
    bank_name = request.POST.get('bank_name')
    bank_slip = request.FILES.get('bank_slip')
    
    if not all([course_id, amount, transaction_id, bank_name]):
        messages.error(request, "All fields are required.")
        return redirect('view-fees')
    
    course = get_object_or_404(Course, id=course_id)
    
    try:
        FeePayment.objects.create(
            student=request.user,
            course=course,
            amount=amount,
            payment_method='Bank Transfer',
            provider=bank_name,
            transaction_id=transaction_id,
            bank_slip=bank_slip,
            status='PENDING' # Needs admin verification
        )
        messages.info(request, "Bank payment submitted for verification.")
    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
        
    return redirect('view-fees')

@login_required
def verify_payments(request, payment_id=None):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
    
    if request.method == 'POST' and payment_id:
        payment = get_object_or_404(FeePayment, id=payment_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            payment.status = 'APPROVED'
            payment.save()
            messages.success(request, f"Approved payment {payment.transaction_id}")
        elif action == 'reject':
            payment.status = 'REJECTED'
            payment.remarks = request.POST.get('remarks', 'Rejected by admin')
            payment.save()
            messages.warning(request, f"Rejected payment {payment.transaction_id}")
            
        return redirect('verify-payments')
        
    # List pending view
    payments = FeePayment.objects.filter(status='PENDING').order_by('-payment_date')
    return render(request, 'accounts/verify_payments.html', {'payments': payments})

# --- Reporting Views ---
from utils.reports import export_to_csv, render_to_pdf

@login_required
def generate_enrollment_report(request):
    if not request.user.role in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
        
    enrollments = Enrollment.objects.all().select_related('student', 'course').order_by('-enrolled_at')
    
    if 'pdf' in request.GET:
        filename = f"Enrollment_Report_{datetime.date.today()}.pdf"
        return render_to_pdf('reports/enrollment_report.html', {'enrollments': enrollments, 'date': datetime.date.today()}, filename=filename)
        
    return export_to_csv(
        enrollments, 
        'enrollment_report', 
        ['student.username', 'student.email', 'course.name', 'enrolled_at'],
        ['Username', 'Email', 'Course', 'Enrolled Date']
    )

@login_required
def generate_payment_report(request):
    if not request.user.role in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
        
    payments = FeePayment.objects.all().select_related('student', 'course').order_by('-payment_date')
    
    if 'pdf' in request.GET:
        filename = f"Payment_Report_{datetime.date.today()}.pdf"
        return render_to_pdf('reports/payment_report.html', {'payments': payments, 'date': datetime.date.today()}, filename=filename)
        
    return export_to_csv(
        payments, 
        'fee_payment_report', 
        ['payment_date', 'student.username', 'student.studentprofile.registration_number', 'course.name', 'amount', 'payment_method', 'transaction_id', 'status'],
        ['Date', 'Student', 'Admin No', 'Course', 'Amount', 'Method', 'Reference', 'Status']
    )
