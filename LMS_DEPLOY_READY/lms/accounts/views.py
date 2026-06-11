from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from utils.reports import export_to_csv, render_to_pdf
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

from assignments.models import Assignment, AssignmentAvailability
from submissions.models import Submission
from courses.models import Cohort, Course, FeePayment, Enrollment, OnlineMeeting, AttendanceRecord
from django.contrib.auth import get_user_model, logout
from .models import PasswordResetRequest
from django.db.models import Sum, Q, Avg, Count
import datetime
import os
import sys
import traceback
from django.conf import settings

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

    from django.core.paginator import Paginator
    from django.db.models import Q
    from courses.models import Cohort

    # All cohorts for filter dropdown
    cohorts = Cohort.objects.all().order_by('name')

    # --- Grades Needing Approval (with cohort filter + pagination) ---
    grades_cohort = request.GET.get('grades_cohort', '')
    grades_search = request.GET.get('grades_search', '')
    grades_page_num = request.GET.get('grades_page', 1)

    pending_grades_qs = Submission.objects.filter(
        is_marked=True, is_approved=False
    ).select_related('student', 'assignment')

    if grades_cohort:
        pending_grades_qs = pending_grades_qs.filter(
            student__enrollments__cohort__id=grades_cohort
        ).distinct()
    if grades_search:
        pending_grades_qs = pending_grades_qs.filter(
            Q(student__username__icontains=grades_search) |
            Q(assignment__title__icontains=grades_search)
        )

    grades_paginator = Paginator(pending_grades_qs.order_by('-submitted_at'), 12)
    pending_grades = grades_paginator.get_page(grades_page_num)

    # Assignments needing approval
    pending_assignments = Assignment.objects.filter(status='PENDING')
    # Payments needing verification
    pending_payments_count = FeePayment.objects.filter(status='PENDING').count()

    # --- Recent Info Lists (with dynamic limits) ---
    def get_limit(param, default=10):
        try:
            val = int(request.GET.get(param, default))
            return val if val in [5, 10, 15, 30, 50, 100, 150] else default
        except (ValueError, TypeError):
            return default

    asg_limit = get_limit('assignments_limit', 10)
    sub_limit = get_limit('submissions_limit', 10)

    assignments = Assignment.objects.all().select_related('course').order_by('-created_at')[:asg_limit]
    submissions = Submission.objects.all().select_related('student', 'assignment').order_by('-submitted_at')[:sub_limit]

    # --- Student Performance Section ---
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
    per_page = get_limit('per_page', 10)

    paginator = Paginator(students_query, per_page)
    page_number = request.GET.get('page')
    students_page = paginator.get_page(page_number)

    # Limit options for all dropdowns
    limit_choices = [5, 10, 15, 30, 50, 100, 150]

    # --- Analytics & Charting Data (Phase 3) ---
    from django.db.models import Sum, Count, F
    from django.db.models.functions import TruncMonth
    import datetime
    from django.utils import timezone

    # 1. Fee Collection Trends (Last 6 Months)
    six_months_ago = timezone.now() - datetime.timedelta(days=180)
    
    def get_monthly_data(status):
        qs = FeePayment.objects.filter(
            status=status, 
            payment_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        return {item['month'].strftime('%b %Y'): float(item['total']) for item in qs}

    approved_map = get_monthly_data('APPROVED')
    pending_map = get_monthly_data('PENDING')

    # Generate labels for the last 6 months to ensure chart isn't empty
    fee_labels = []
    approved_data = []
    pending_data = []
    
    for i in range(5, -1, -1):
        d = timezone.now() - datetime.timedelta(days=i*30)
        label = d.strftime('%b %Y')
        fee_labels.append(label)
        approved_data.append(approved_map.get(label, 0.0))
        pending_data.append(pending_map.get(label, 0.0))

    # 2. Grade Distribution
    grade_dist_qs = Submission.objects.filter(is_marked=True).values('grade').annotate(count=Count('grade'))
    grade_labels = []
    grade_data = []
    grade_colors = []
    
    grade_map = {'P': 'Pass', 'F': 'Fail'}
    color_map = {'P': '#10b981', 'F': '#f43f5e'} # Emerald-500, Rose-500

    for item in grade_dist_qs:
        g = item['grade']
        grade_labels.append(grade_map.get(g, g))
        grade_data.append(item['count'])
        grade_colors.append(color_map.get(g, '#64748b'))

    # 3. Submission Statistics
    total_enrollments = Enrollment.objects.count()
    total_submissions = Submission.objects.count()
    
    # Cap ratio at 100% for visual sanity if needed, but here we just pass the raw % 
    # and we'll handle the width cap in the template.
    submission_ratio = (total_submissions / total_enrollments * 100) if total_enrollments > 0 else 0
    
    # Pack for template
    analytics = {
        'fee_labels': fee_labels,
        'approved_data': approved_data,
        'pending_data': pending_data,
        'grade_labels': grade_labels,
        'grade_data': grade_data,
        'grade_colors': grade_colors,
        'total_enrollments': total_enrollments,
        'total_submissions': total_submissions,
        'submission_ratio': submission_ratio,
    }

    return render(request, 'admin_dashboard.html', {
        'assignments': assignments,
        'submissions': submissions,
        'students': students_page,
        'search_query': search_query,
        'per_page': per_page,
        'asg_limit': asg_limit,
        'sub_limit': sub_limit,
        'limit_choices': limit_choices,
        'pending_assignments': pending_assignments,
        'pending_grades': pending_grades,
        'pending_payments_count': pending_payments_count,
        'cohorts': cohorts,
        'grades_cohort': grades_cohort,
        'grades_search': grades_search,
        'analytics': analytics,
    })


# Lecturer Dashboard
@login_required
def lecturer_dashboard(request):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to view this page.")
    
    from django.core.cache import cache
    from courses.models import Cohort, Module, OnlineMeeting, Resource
    from communications.models import Notice, DiscussionMessage, Ticket
    
    # 1. Identify assigned cohorts (Relatively cheap)
    assigned_cohorts = Cohort.objects.filter(lecturers=request.user)
    
    # 2. Optimized Assignments Fetch
    assignments_qs = Assignment.objects.filter(
        course__cohort__in=assigned_cohorts
    ).select_related('module', 'course', 'course__cohort').order_by('sort_key')
    
    # Cache key unique to this lecturer
    cache_key = f"lecturer_stats_{request.user.id}"
    stats = cache.get(cache_key)
    
    if not stats:
        # Complex counts handled in one pass if possible, or cached for performance
        pending_count = Submission.objects.filter(assignment__in=assignments_qs, is_marked=False).count()
        stats = {'pending_count': pending_count}
        cache.set(cache_key, stats, 60) # Cache for 60 seconds
    
    pending_count = stats['pending_count']

    # 3. Submissions needing marking (Limited & Optimized)
    def get_limit(param, default=10):
        try:
            val = int(request.GET.get(param, default))
            return val if val in [5, 10, 15, 30, 50, 100, 150] else default
        except (ValueError, TypeError):
            return default

    p_limit = get_limit('pending_limit', 10)
    m_limit = get_limit('marked_limit', 10)

    pending_submissions = Submission.objects.filter(
        assignment__in=assignments_qs, 
        is_marked=False
    ).select_related('student', 'assignment', 'assignment__module').order_by('-submitted_at')[:p_limit]
    
    marked_submissions = Submission.objects.filter(
        assignment__in=assignments_qs, 
        is_marked=True
    ).select_related('student', 'assignment', 'assignment__module').order_by('-submitted_at')[:m_limit]

    # 4. Content Grouping (In-memory is faster than extra DB calls)
    from assignments.models import AssignmentAvailability
    availabilities = AssignmentAvailability.objects.filter(
        assignment__in=assignments_qs,
        cohort__in=assigned_cohorts
    )
    avail_map = {(a.assignment_id, a.cohort_id): a for a in availabilities}
    
    assignments_by_module = {}
    for a in assignments_qs:
        if a.course.cohort_id:
            a.lecturer_availability = avail_map.get((a.id, a.course.cohort_id))

        mod_name = a.module.name if a.module else f"General Assignments"
        if mod_name not in assignments_by_module:
            assignments_by_module[mod_name] = []
        assignments_by_module[mod_name].append(a)

    # 5. Ancillary Data (Notices, Meetings, etc.)
    meetings = OnlineMeeting.objects.filter(cohort__in=assigned_cohorts).order_by('-meeting_date').select_related('cohort')[:5]
    resources = list(Resource.objects.all().order_by('order', 'title'))
    
    notices = Notice.objects.filter(
        Q(cohort__in=assigned_cohorts) | Q(cohort__isnull=True),
        is_active=True
    ).select_related('author', 'cohort').order_by('-created_at')[:5]

    discussions = DiscussionMessage.objects.filter(
        assignment__in=assignments_qs
    ).select_related('sender', 'assignment').order_by('-created_at')[:5]

    tickets = Ticket.objects.filter(
        cohort__in=assigned_cohorts,
        status__in=['OPEN', 'IN_PROGRESS']
    ).select_related('student', 'cohort').order_by('-updated_at')[:5]
    
    return render(request, 'lecturer_dashboard.html', {
        'cohorts': assigned_cohorts,
        'assignments_by_module': assignments_by_module,
        'pending_submissions': pending_submissions,
        'marked_submissions': marked_submissions,
        'pending_limit': p_limit,
        'marked_limit': m_limit,
        'limit_choices': [5, 10, 15, 30, 50, 100, 150],
        'meetings': meetings,
        'pending_count': pending_count,
        'resources': resources,
        'notices': notices,
        'discussions': discussions,
        'tickets': tickets,
    })

@login_required
def student_submissions_report(request, student_id):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to view this report.")
    
    student = get_object_or_404(User, id=student_id, role='STUDENT')
    
    from courses.models import Cohort, Enrollment
    from assignments.models import Assignment, AssignmentAvailability

    # Lecturers only see students in cohorts they are assigned to
    if not request.user.is_superuser:
        assigned_cohorts = Cohort.objects.filter(lecturers=request.user)
        student_in_assigned_cohort = Enrollment.objects.filter(student=student, cohort__in=assigned_cohorts).exists()
        if not student_in_assigned_cohort:
            raise Http404("You are not authorized to view this student's report.")

    # Get all enrollments for student
    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'cohort')
    cohort_ids = [e.cohort_id for e in enrollments if e.cohort_id]
    
    # Get all assignments available to this student's cohorts
    assignments_qs = Assignment.objects.filter(
        availabilities__cohort_id__in=cohort_ids,
        status='APPROVED'
    ).select_related('module', 'course').distinct()
    
    # Get all submissions for these assignments by this student
    submissions = Submission.objects.filter(student=student, assignment__in=assignments_qs).select_related('assignment')
    submission_map = {s.assignment_id: s for s in submissions}
    
    # Get availabilities for deadlines
    availabilities = AssignmentAvailability.objects.filter(
        assignment__in=assignments_qs,
        cohort_id__in=cohort_ids
    )
    avail_map = {(a.assignment_id, a.cohort_id): a for a in availabilities}

    # Group data by cohort
    report_data = []
    for enrollment in enrollments:
        cohort = enrollment.cohort
        if not cohort: continue
        
        cohort_assignments = []
        for assignment in assignments_qs:
            # Check if this assignment is available for THIS cohort
            availability = avail_map.get((assignment.id, cohort.id))
            if availability:
                submission = submission_map.get(assignment.id)
                cohort_assignments.append({
                    'assignment': assignment,
                    'availability': availability,
                    'submission': submission,
                })
        
        # Sort by module version number (1.0.0 → N.N.N)
        import re as _re3
        def _report_version_key(item):
            m = _re3.match(r'^(\d+)\.?(\d*)\.?(\d*)', item['assignment'].title.strip())
            if m:
                return (int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0))
            return (9999, 9999, 9999)
        cohort_assignments.sort(key=_report_version_key)

        if cohort_assignments:
            graded_submissions = [a['submission'] for a in cohort_assignments if a['submission'] and a['submission'].is_marked and getattr(a['submission'], 'marks_awarded', None) is not None]
            avg_marks = sum(s.marks_awarded for s in graded_submissions) / len(graded_submissions) if graded_submissions else None

            report_data.append({
                'cohort': cohort,
                'course': enrollment.course,
                'assignments': cohort_assignments,
                'avg_marks': avg_marks,
            })
            
    all_graded = [s for s in submissions if s.is_marked and getattr(s, 'marks_awarded', None) is not None]
    overall_avg = sum(s.marks_awarded for s in all_graded) / len(all_graded) if all_graded else None
        
    return render(request, 'student_report.html', {
        'student': student,
        'report_data': report_data,
        'overall_avg': overall_avg,
    })

@login_required
def cohort_student_submissions(request, cohort_id):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to view this page.")
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Check if lecturer has access to this cohort
    if not request.user.is_superuser:
        if not cohort.lecturers.filter(id=request.user.id).exists():
            raise Http404("You are not authorized to view students in this cohort.")

    from courses.models import Enrollment
    enrollments = Enrollment.objects.filter(cohort=cohort).select_related('student').order_by('student__username')
    
    return render(request, 'cohort_students.html', {
        'cohort': cohort,
        'enrollments': enrollments,
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
    from courses.models import Module
    available_assignments_queryset = Assignment.objects.filter(
        availabilities__cohort__in=[e.course.cohort for e in enrollments],
        status='APPROVED'
    ).exclude(id__in=submitted_ids).select_related('module').distinct()

    # Prefetch availabilities for efficency
    student_cohort_ids = [e.course.cohort_id for e in enrollments if e.course.cohort]
    availabilities = AssignmentAvailability.objects.filter(
        assignment__in=available_assignments_queryset,
        cohort_id__in=student_cohort_ids
    )
    avail_map = {(a.assignment_id, a.cohort_id): a for a in availabilities}
    
    # Map Assignment -> Course -> Cohort (via Enrollment)
    # We need to match assignment to the student's cohort for that course
    course_cohort_map = {e.course_id: e.course.cohort_id for e in enrollments if e.course.cohort}
    
    for assignment in available_assignments_queryset:
        c_id = course_cohort_map.get(assignment.course_id)
        if c_id:
            assignment.student_availability = avail_map.get((assignment.id, c_id))


    # Group assignments by module
    assignments_by_module = {}
    for assignment in available_assignments_queryset:
        if assignment.module:
            mod_name = assignment.module.name
        else:
            mod_name = f"{assignment.course.cohort.name} Assignments"
            
        if mod_name not in assignments_by_module:
            assignments_by_module[mod_name] = []
        assignments_by_module[mod_name].append(assignment)

    # Sort modules numerically (Module 1 → Module 2 → ... → Module N)
    import re as _re
    def _mod_sort_key(name):
        m = _re.search(r'\d+', name)
        return int(m.group()) if m else 9999
    assignments_by_module = dict(sorted(assignments_by_module.items(), key=lambda x: _mod_sort_key(x[0])))

    # --- Optimized Attendance Aggregation ---
    from django.db.models import Avg, Count, Sum
    from django.utils import timezone
    
    cohort_ids = [e.course.cohort_id for e in enrollments if e.course.cohort]
    now = timezone.now()
    
    # Get total meetings per cohort
    total_meetings_map = {
        m['cohort_id']: m['count']
        for m in OnlineMeeting.objects.filter(cohort_id__in=cohort_ids, meeting_date__lte=now)
        .values('cohort_id').annotate(count=Count('id'))
    }
    
    # Get attended count per cohort
    attended_counts_map = {
        a['meeting__cohort_id']: a['count']
        for a in AttendanceRecord.objects.filter(student=request.user, meeting__cohort_id__in=cohort_ids, is_attended=True)
        .values('meeting__cohort_id').annotate(count=Count('id'))
    }
    
    # Get active meeting for each cohort (latest one)
    all_recent_meetings = OnlineMeeting.objects.filter(cohort_id__in=cohort_ids).annotate(
        attendance_count=Count('attendance_logs')
    ).order_by('cohort_id', '-meeting_date')
    active_meetings = {}
    for m in all_recent_meetings:
        if m.cohort_id not in active_meetings:
            active_meetings[m.cohort_id] = m

    attendance_data = []
    for enrollment in enrollments:
        cohort_id = enrollment.course.cohort_id
        total_meetings = total_meetings_map.get(cohort_id, 0)
        attended_count = attended_counts_map.get(cohort_id, 0)
        
        active_meeting = active_meetings.get(cohort_id)
        is_live = active_meeting.is_active if active_meeting else False
        
        if is_live:
            # Auto-mark attendance
            is_punctual = active_meeting.is_punctual(now)
            AttendanceRecord.objects.update_or_create(
                meeting=active_meeting,
                student=request.user,
                defaults={'is_attended': is_punctual}
            )
            # Adjust attended count in memory if it was just created/updated to True
            # For simplicity, we can just say if is_punctual is True and it wasn't counted, we could increment.
            # But re-fetching counts is safer if we want 100% accuracy, though slightly slower.
            # Let's keep it simple: the next refresh will have the perfect count.
        
        percentage = (attended_count / total_meetings * 100) if total_meetings > 0 else 0
        attendance_data.append({
            'course_id': enrollment.course.id,
            'percentage': round(percentage, 1),
            'perfect': attended_count == total_meetings and total_meetings > 0,
            'active_meeting': active_meeting if is_live else None
        })

    # --- Optimized Certificate Eligibility ---
    # Assignment totals per course
    assignment_totals = {
        a['course_id']: a['count']
        for a in Assignment.objects.filter(course__in=[e.course for e in enrollments], status='APPROVED')
        .values('course_id').annotate(count=Count('id'))
    }
    
    # Graded submissions per course
    graded_info = {
        s['assignment__course_id']: {'count': s['count'], 'avg': s['avg']}
        for s in Submission.objects.filter(student=request.user, assignment__course__in=[e.course for e in enrollments], is_marked=True)
        .values('assignment__course_id').annotate(count=Count('id'), avg=Avg('percentage'))
    }
    
    # Fee payments per course
    fee_info = {
        p['course_id']: p['total']
        for p in FeePayment.objects.filter(student=request.user, course__in=[e.course for e in enrollments], status='APPROVED')
        .values('course_id').annotate(total=Sum('amount'))
    }

    certificate_eligibility = []
    for enrollment in enrollments:
        course = enrollment.course
        total_assignments = assignment_totals.get(course.id, 0)
        info = graded_info.get(course.id, {'count': 0, 'avg': 0})
        graded_submissions_count = info['count']
        course_avg = info['avg'] or 0
        total_paid = fee_info.get(course.id, 0)
        
        all_graded = (total_assignments == graded_submissions_count) if total_assignments > 0 else False
        has_passing_grade = course_avg >= 50
        balance = course.fee - total_paid
        fees_cleared = balance <= 0
        
        # Determine base (AUTO) eligibility
        can_download = all_graded and has_passing_grade and fees_cleared
        
        # Apply Overrides
        override = enrollment.certificate_lock_override
        if override == 'LOCKED':
            can_download = False
            reason = "Locked by Admin"
        elif override == 'UNLOCKED':
            can_download = True
            reason = "Certificate available (Manual Unlock)"
        else:
            # AUTO: use the base logic
            if not all_graded:
                reason = f"Complete all {total_assignments} assignments ({graded_submissions_count}/{total_assignments} graded)"
            elif not has_passing_grade:
                reason = f"Achieve passing grade (current: {course_avg:.1f}%, required: 50%)"
            elif not fees_cleared:
                reason = f"Clear outstanding fees (KES {balance:,.2f})"
            else:
                reason = "Certificate available"
        
        certificate_eligibility.append({
            'course': course,
            'can_download': can_download,
            'reason': reason,
            'completion_percentage': (graded_submissions_count / total_assignments * 100) if total_assignments > 0 else 0,
            'average_grade': course_avg
        })
    
    # Limit "Recent Work" display
    limit_str = request.GET.get('limit', '10')
    try:
        limit = int(limit_str)
        if limit < 1:
            limit = 10
    except ValueError:
        limit = 10
        
    limit_options = []
    for val in [10, 30, 50, 100]:
        limit_options.append({
            'value': val,
            'selected': True if limit == val else False
        })
        
    # Sort recent work by assignment module version (e.g. 1.0.0 → 2.3.7 → 2.9.2)
    import re as _re2
    def _version_sort_key(sub):
        # Priority: 0 for Fail, 1 for Pass (Failed work comes first)
        priority = 0 if sub.grade == 'F' else 1
        
        m = _re2.match(r'^(\d+)\.?(\d*)\.?(\d*)', sub.assignment.title.strip())
        if m:
            v_tuple = (int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0))
        else:
            v_tuple = (9999, 9999, 9999)
        
        return (priority, v_tuple)

    _all_submissions = list(submissions.select_related('assignment'))
    _all_submissions.sort(key=_version_sort_key)
    recent_submissions = _all_submissions[:limit]


    # --- Transcript eligibility (70% fee rule) ---
    transcript_total_fees = sum(e.course.fee for e in enrollments)
    transcript_total_paid = sum(fee_info.get(e.course.id, 0) for e in enrollments)
    transcript_fee_percent = (transcript_total_paid / transcript_total_fees * 100) if transcript_total_fees > 0 else 0
    
    # Apply Transcript Overrides
    profile = getattr(request.user, 'studentprofile', None)
    t_override = profile.transcript_lock_override if profile else 'AUTO'
    
    if t_override == 'LOCKED':
        transcript_eligible = False
    elif t_override == 'UNLOCKED':
        transcript_eligible = True
    else:
        transcript_eligible = transcript_fee_percent >= 70

    # --- Resource Hub & Progress Tracker ---
    from courses.models import Resource
    resources = list(Resource.objects.filter(is_active=True).order_by('order', 'title'))
    resources.sort(key=lambda x: _mod_sort_key(x.title))
    
    # Calculate overall progress (graded assignments / total assigned)
    total_assigned = sum(assignment_totals.values())
    total_graded = sum(v['count'] for v in graded_info.values())
    overall_progress = (total_graded / total_assigned * 100) if total_assigned > 0 else 0

    # Upcoming Deadlines & Exams
    # We want assignments that Haven't been submitted yet and have a deadline in the future
    upcoming_assignments = Assignment.objects.filter(
        availabilities__cohort__in=[e.course.cohort for e in enrollments if e.course.cohort],
        status='APPROVED',
        availabilities__deadline__gt=now
    ).exclude(id__in=submitted_ids).select_related('course', 'module').distinct()

    upcoming_exams = upcoming_assignments.filter(is_exam=True)
    upcoming_labs = upcoming_assignments.filter(is_exam=False)

    # --- Notice Board (Global & Cohort-specific) ---
    from communications.models import Notice
    notices = Notice.objects.filter(
        (Q(cohort__isnull=True) & Q(recipient__isnull=True)) |   # Global notices (no cohort, no recipient)
        (Q(cohort__in=[e.course.cohort for e in enrollments if e.course.cohort]) & Q(recipient__isnull=True)) |  # Cohort-wide notices (not individual)
        Q(recipient=request.user),                                # Individual notices ONLY for this user
        is_active=True
    ).select_related('author', 'cohort')

    return render(request, 'student_dashboard.html', {
        'submissions': recent_submissions,
        'selected_limit': limit,
        'assignments_by_module': assignments_by_module,
        'enrollments': enrollments,
        'avg_mark': round(avg_mark, 2),
        'pass_status': pass_status,
        'all_over': all_over,
        'attendance_data': attendance_data,
        'meetings': all_recent_meetings,
        'certificate_eligibility': certificate_eligibility,
        'transcript_eligible': transcript_eligible,
        'transcript_fee_percent': round(transcript_fee_percent, 1),
        'notices': notices,
        'resources': resources,
        'overall_progress': round(overall_progress, 1),
        'upcoming_exams': upcoming_exams,
        'upcoming_labs': upcoming_labs,
        'limit_options': limit_options,
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
                    send_mail(subject_admin, message_admin, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=False)

                # Notify User
                subject_user = "Password Reset Request Submitted"
                message_user = f"Dear {user.username},\n\nYour password reset request has been received and is pending Admin approval. You will receive another email once it has been reviewed."
                if user.email:
                    send_mail(subject_user, message_user, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)

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

        # Notify User of Approval/Rejection
        user = reset_req.user
        if user.email:
            if action == 'approve':
                subject = "Password Reset Approved"
                message = f"Dear {user.username},\n\nYour password reset request has been approved and your new password has been applied. You can now log in with your new password."
            else:
                subject = "Password Reset Rejected"
                comment = reset_req.admin_comment or "No additional comments."
                message = f"Dear {user.username},\n\nYour password reset request has been rejected.\nAdmin Comment: {comment}"
            
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)

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
    
    # Check for existing submission
    existing_submission = Submission.objects.filter(student=request.user, assignment=assignment).first()
    
    if request.method == 'POST':
        # Check if submission is locked
        if existing_submission and existing_submission.is_locked:
            messages.error(request, "This submission is locked (graded). Please contact your lecturer to unlock it if you need to resubmit.")
            return redirect('submit-assignment', assignment_id=assignment_id)

        submission_files = request.FILES.getlist('submission_files')
        if len(submission_files) < 3:
            messages.error(request, "Please upload at least 3 files (pdf, pka and screenshot)")
            return redirect('submit-assignment', assignment_id=assignment_id)

        # Handle file creation/update
        if existing_submission:
            submission = existing_submission
            submission.last_submitted_at = timezone.now()
            # Clear previous marks/grade for fresh attempt
            submission.marks_awarded = None
            submission.is_marked = False
            submission.grade = ""
            submission.percentage = None
            submission.save()
            # Delete old files
            submission.files.all().delete()
        else:
            submission = Submission.objects.create(student=request.user, assignment=assignment)
        
        from submissions.models import SubmissionFile
        for file in submission_files:
            SubmissionFile.objects.create(
                submission=submission, 
                file=file,
                original_name=file.name
            )
            
            
        from utils.emails import send_mail_background
        lecturers = assignment.course.cohort.lecturers.all()
        lecturer_emails = [l.email for l in lecturers if l.email]
        if lecturer_emails:
            subject = f"New Submission: {assignment.title} - {request.user.username}"
            message = f"Student {request.user.username} has submitted their assignment for '{assignment.title}'.\nLog in to the dashboard to grade it."
            send_mail_background(subject, message, lecturer_emails)

        messages.success(request, f"Assignment '{assignment.title}' submitted successfully!")
        return redirect('student-dashboard')
    
    # Check availability constraints
    can_submit = True
    reason = ""
    
    # 1. Deadline Check
    from django.utils import timezone
    now = timezone.now()
    availability = AssignmentAvailability.objects.filter(assignment=assignment, cohort__courses__enrollments__student=request.user).first()
    
    effective_deadline = availability.deadline if availability else None
        
    is_late = False
    if effective_deadline and now > effective_deadline:
        if availability and availability.allow_late:
            if availability.late_until and now > availability.late_until:
                can_submit = False
                reason = "Late submission deadline has passed."
            else:
                is_late = True
        else:
            can_submit = False
            reason = "Deadline has passed."
            
    return render(request, 'submit_assignment.html', {
        'assignment': assignment,
        'existing_submission': existing_submission,
        'can_submit': can_submit,
        'reason': reason,
        'is_late': is_late
    })

@login_required
@require_POST
def delete_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    
    if submission.student != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect('student-dashboard')
        
    if submission.is_locked:
        messages.error(request, "Cannot delete a locked submission.")
        return redirect('submit-assignment', assignment_id=submission.assignment.id)
        
    # Check deadline
    from django.utils import timezone
    now = timezone.now()
    availability = AssignmentAvailability.objects.filter(assignment=submission.assignment, cohort__courses__enrollments__student=request.user).first()
    effective_deadline = availability.deadline if availability else None
    
    # Allow deletion if late submission is allowed, otherwise strictly block if deadline passed
    allow_late = availability.allow_late if availability else False
    late_until = availability.late_until if availability else None
    
    if effective_deadline and now > effective_deadline:
        if not allow_late or (late_until and now > late_until):
             messages.error(request, "Cannot delete submission after the deadline.")
             return redirect('submit-assignment', assignment_id=submission.assignment.id)

    assignment_id = submission.assignment.id
    submission.delete()
    messages.success(request, "Submission deleted. You can now upload a new version.")
    return redirect('submit-assignment', assignment_id=assignment_id)

@login_required
@require_POST
def reset_submission(request, submission_id):
    if request.user.role != 'LECTURER' and not request.user.is_superuser:
        messages.error(request, "Unauthorized.")
        return redirect('home')
        
    submission = get_object_or_404(Submission, id=submission_id)
    
    # Reset grading status to allow student to delete
    submission.is_marked = False
    submission.is_locked = False
    submission.marks_awarded = None
    submission.percentage = None
    submission.grade = ""
    submission.save()
    
    messages.success(request, f"Submission for {submission.student.username} has been unlocked. They can now delete and resubmit.")
    return redirect('lecturer-dashboard')

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
            # submission.save() will handle percentage and grade calculation logic
            submission.save()

            # Notify Student (Background)
            from utils.emails import send_mail_background
            if submission.student.email:
                subject = f"Assignment Graded: {submission.assignment.title}"
                # Safely get percentage for email
                perc = (submission.percentage if submission.percentage is not None else 0.0)
                message = (
                    f"Dear {submission.student.username},\n\n"
                    f"Your submission for '{submission.assignment.title}' has been graded.\n"
                    f"Score: {submission.marks_awarded}/{submission.assignment.total_marks} ({perc:.1f}%)\n"
                    f"Feedback: {submission.feedback}"
                )
                send_mail_background(subject, message, [submission.student.email])

            messages.success(request, f"Marked {submission.student.username}'s submission.")
        except Exception as e:
            messages.error(request, f"Error saving grade: {str(e)}")
            # In a real production app, you might log this:
            # print(f"Grading error: {e}")
            # traceback.print_exc()
            
        return redirect('lecturer-dashboard')
    return render(request, 'grade_submission.html', {'submission': submission})

# Assignment Creation (Lecturers)
from assignments.forms import AssignmentForm
@login_required
def create_assignment(request):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to create assignments.")
    
    from courses.models import Course, Cohort, Module
    assigned_cohorts = Cohort.objects.filter(lecturers=request.user)


    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.created_by = request.user
            assignment.status = 'PENDING'
            
            # Get the cohort from form
            cohort = form.cleaned_data['cohort']
            
            # Auto-derive course from cohort
            cohort_course = cohort.courses.first()
            if not cohort_course:
                messages.error(request, f"Cohort '{cohort}' has no associated course. Please contact admin.")
                return render(request, 'create_assignment.html', {'form': form})
            
            assignment.course = cohort_course
            
            # Validate cohort is assigned to lecturer
            if not request.user.is_superuser and cohort not in assigned_cohorts:
                messages.error(request, "Invalid cohort selected.")
            # Validate module belongs to the course (if module is provided)
            elif assignment.module and assignment.module.course != assignment.course:
                messages.error(request, f"Selected module does not belong to {assignment.course.name}.")
            else:
                assignment.save()
                
                # Create/Update Availability
                AssignmentAvailability.objects.update_or_create(
                    assignment=assignment,
                    cohort=cohort,
                    defaults={
                        'deadline': form.cleaned_data['deadline'],
                        'allow_late': form.cleaned_data['allow_late'],
                        'late_until': form.cleaned_data['late_until'],
                        'created_by': request.user
                    }
                )

                messages.success(request, f"✅ Assignment '{assignment.title}' created and sent for admin approval!")
                return redirect('lecturer-dashboard')
        else:
            # Form validation failed - show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssignmentForm()
        # Filter cohorts in the form
        if not request.user.is_superuser:
            form.fields['cohort'].queryset = assigned_cohorts
            
    # Build cohort -> modules map for dynamic filtering
    import json
    cohort_modules = {}
    
    # Use the queryset available to the user (superuser gets all, lecturer gets assigned)
    target_cohorts = assigned_cohorts if not request.user.is_superuser else Cohort.objects.all()
    
    for c in target_cohorts:
        # Assuming 1 course per cohort as per current structure
        course = c.courses.first()
        if course:
            modules = list(course.modules.values('id', 'name').order_by('order', 'name'))
            cohort_modules[c.id] = modules
        else:
            cohort_modules[c.id] = []
            
    return render(request, 'create_assignment.html', {
        'form': form, 
        'cohort_modules': cohort_modules
    })

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

    # Notify Student of Approval (Background)
    from utils.emails import send_mail_background
    if submission.student.email:
        subject = f"Grade Approved: {submission.assignment.title}"
        message = f"Dear {submission.student.username},\n\nYour grade for '{submission.assignment.title}' has been approved by the Admin and is now locked."
        send_mail_background(subject, message, [submission.student.email])

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
    
    users_query = User.objects.all().select_related('studentprofile').order_by('role', 'username')
    from django.core.paginator import Paginator
    paginator = Paginator(users_query, 20)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
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
        
        elif action == 'update_reg_no':
            user_to_update = get_object_or_404(User, id=user_id)
            reg_no = request.POST.get('registration_number', '').strip()
            if user_to_update.role == 'STUDENT':
                from .models import StudentProfile
                profile, _ = StudentProfile.objects.get_or_create(user=user_to_update)
                profile.registration_number = reg_no
                profile.save()
                messages.success(request, f"Updated registration number for {user_to_update.username} to {reg_no}")
            else:
                messages.error(request, "Registration numbers can only be set for students.")
            
        return redirect('manage-users')

    if request.method == 'POST' and 'create_user' in request.POST:
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'STUDENT')
        reg_no = request.POST.get('registration_number', '').strip()
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            new_user = User.objects.create_user(username=username, email=email, password=password)
            new_user.role = role
            new_user.save()
            
            if role == 'STUDENT' and reg_no:
                from .models import StudentProfile
                profile, _ = StudentProfile.objects.get_or_create(user=new_user)
                profile.registration_number = reg_no
                profile.save()
                
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

# --- Student Portal Views ---

# --- New Features for Student Portal ---

@login_required
def view_fees(request):
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can view fees.")
    
    enrollments = Enrollment.objects.filter(student=request.user)
    fee_data = []
    
    all_payments = FeePayment.objects.filter(student=request.user).select_related('course').order_by('-payment_date')
    
    from collections import defaultdict
    payments_by_course = defaultdict(list)
    for p in all_payments:
        payments_by_course[p.course_id].append(p)
    
    fee_data = []
    
    for enrollment in enrollments:
        course = enrollment.course
        payments = payments_by_course.get(course.id, [])
        # Only count approved (and pending) payments towards the total paid. Exclude rejected.
        total_paid = sum(p.amount for p in payments if p.status != 'REJECTED')
        
        # Calculate available credit for transfer (ONLY from APPROVED payments)
        total_approved = sum(p.amount for p in payments if p.status == 'APPROVED')
        # Subtract any pending transfers OUT from this course to prevent double spending
        pending_out = sum(abs(p.amount) for p in payments if p.payment_method == 'Fee Transfer' and p.amount < 0 and p.status == 'PENDING')
        
        available_credit = max(0, total_approved - course.fee - pending_out)
        
        balance = course.fee - total_paid
        
        fee_data.append({
            'course': course,
            'payments': payments,
            'total_paid': total_paid,
            'balance': balance,
            'available_credit': available_credit
        })
        
    has_any_credit = any(d['available_credit'] > 0 for d in fee_data)
    return render(request, 'student_fees.html', {'fee_data': fee_data, 'has_any_credit': has_any_credit})

@login_required
@require_POST
def transfer_fee(request):
    if request.user.role != 'STUDENT':
        raise Http404()
        
    transfer_type = request.POST.get('transfer_type', 'internal')
    to_course_id = request.POST.get('to_course_id')
    amount_str = request.POST.get('amount', '0')
    evidence = request.FILES.get('evidence')
    
    try:
        amount = Decimal(amount_str)
    except Exception:
        messages.error(request, "Invalid amount.")
        return redirect('view-fees')
    
    if not evidence:
        messages.error(request, "Please attach relevant documents (e.g. Transfer Letter or Slip) for confirmation.")
        return redirect('view-fees')

    if not to_course_id or amount <= 0:
        messages.error(request, "Invalid transfer request.")
        return redirect('view-fees')
        
    to_course = get_object_or_404(Course, id=to_course_id)
    # Ensure student is enrolled in target
    get_object_or_404(Enrollment, student=request.user, course=to_course)
    
    timestamp = timezone.now().strftime('%y%m%d%H%M')
    
    if transfer_type == 'internal':
        from_course_id = request.POST.get('from_course_id')
        if not from_course_id or from_course_id == to_course_id:
            messages.error(request, "Cannot transfer fee to the same course.")
            return redirect('view-fees')
            
        from_course = get_object_or_404(Course, id=from_course_id)
        # Ensure student is enrolled in source
        get_object_or_404(Enrollment, student=request.user, course=from_course)
        
        # Verify internal credit (Approved - Fee - Pending Out)
        payments = FeePayment.objects.filter(student=request.user, course=from_course)
        total_approved = payments.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        pending_out_val = payments.filter(payment_method='Fee Transfer', amount__lt=0, status='PENDING').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        # pending_out_val is negative, so adding it subtracts the absolute amount
        available_credit = total_approved - from_course.fee + pending_out_val
        
        if amount > available_credit:
            messages.error(request, f"Insufficient internal credit in {from_course.name}. Available: KES {available_credit:,.2f}")
            return redirect('view-fees')
            
        # Create PENDING transfer records for admin confirmation
        # 1. Record the deduction from source (will be finalized when approved)
        FeePayment.objects.create(
            student=request.user,
            course=from_course,
            amount=-amount,
            payment_method='Fee Transfer',
            provider='Internal Transfer',
            transaction_id=f"TRF-OUT-{from_course.id}-{timestamp}",
            status='PENDING',
            bank_slip=evidence,
            remarks=f"Pending transfer to {to_course.name}"
        )
        
        # 2. Record the addition to target
        FeePayment.objects.create(
            student=request.user,
            course=to_course,
            amount=amount,
            payment_method='Fee Transfer',
            provider='Internal Transfer',
            transaction_id=f"TRF-IN-{to_course.id}-{timestamp}",
            status='PENDING',
            bank_slip=evidence,
            remarks=f"Pending transfer from {from_course.name}"
        )
    else:
        # External Transfer (e.g. from University)
        institution = request.POST.get('institution', 'External Institution').strip()
        if not institution:
            messages.error(request, "Please specify the institution you are transferring from.")
            return redirect('view-fees')
            
        FeePayment.objects.create(
            student=request.user,
            course=to_course,
            amount=amount,
            payment_method='Fee Transfer',
            provider=institution,
            transaction_id=f"EXT-TRF-{timestamp}",
            status='PENDING',
            bank_slip=evidence,
            remarks=f"External fee transfer from {institution}"
        )
    
    messages.info(request, "Fee transfer request and documents submitted. Admin will verify shortly.")
    return redirect('view-fees')

@login_required
def download_fee_statement(request, course_id):
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can download fee statements.")
        
    course = get_object_or_404(Course, id=course_id)
    # Ensure enrollment
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
        
    payments = FeePayment.objects.filter(student=request.user, course=course, status='APPROVED').order_by('payment_date')
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = course.fee - total_paid
    
    # Absolute path for Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'academy_combined_logo.png')
    
    context = {
        'student': request.user,
        'course': course,
        'enrollment': enrollment,
        'payments': payments,
        'total_paid': total_paid,
        'balance': balance,
        'date': datetime.date.today(),
        'logo_path': logo_path if os.path.exists(logo_path) else None,
    }
    
    from utils.reports import render_to_pdf
    filename = f"Fee_Statement_{request.user.username}_{course.id}.pdf"
    return render_to_pdf('pdf/fee_statement.html', context, filename=filename)

@login_required
def download_transcript(request):
    """Generate comprehensive transcript for all enrolled courses"""
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can download transcripts.")
    
    # Get all enrollments
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__cohort')
    
    if not enrollments.exists():
        messages.error(request, "You are not enrolled in any courses.")
        return redirect('student-dashboard')

    # --- Lock Override Logic ---
    profile = getattr(request.user, 'studentprofile', None)
    override = profile.transcript_lock_override if profile else 'AUTO'
    
    if override == 'LOCKED':
        messages.error(request, "Transcript is locked by Admin.")
        return redirect('student-dashboard')
    elif override == 'UNLOCKED':
        # Skip fee check
        fee_percent = 100 # For display purposes or just bypass
    else:
        # --- 70% Fee Rule ---
        total_fees = sum(e.course.fee for e in enrollments)
        total_approved = FeePayment.objects.filter(
            student=request.user,
            course__in=[e.course for e in enrollments],
            status='APPROVED'
        ).aggregate(total=Sum('amount'))['total'] or 0

        fee_percent = (total_approved / total_fees * 100) if total_fees > 0 else 0

        if fee_percent < 70:
            messages.error(
                request,
                f"Transcript locked. You have paid {fee_percent:.1f}% of your fees. "
                f"A minimum of 70% payment is required to download your transcript."
            )
            return redirect('view-fees')
    # --- End Lock Logic ---
    transcript_data = []
    overall_submissions = []
    
    # Fetch all graded submissions for the student once
    all_graded_submissions = Submission.objects.filter(
        student=request.user,
        is_marked=True
    ).select_related('assignment', 'assignment__course').order_by('assignment__course_id', 'submitted_at')
    
    # Group by course_id for easy lookup
    from collections import defaultdict
    submissions_by_course = defaultdict(list)
    for s in all_graded_submissions:
        submissions_by_course[s.assignment.course_id].append(s)
    
    transcript_data = []
    overall_submissions = []
    
    for enrollment in enrollments:
        course = enrollment.course
        submissions = submissions_by_course.get(course.id, [])
        
        if submissions:
            course_avg = sum(s.percentage for s in submissions) / len(submissions)
            pass_status = "PASS" if course_avg >= 50 else "FAIL"
            
            transcript_data.append({
                'course': course,
                'submissions': submissions,
                'avg_mark': course_avg,
                'pass_status': pass_status,
            })
            
            overall_submissions.extend(submissions)
    
    # Calculate overall average
    if overall_submissions:
        overall_avg = sum(s.percentage for s in overall_submissions) / len(overall_submissions)
    else:
        overall_avg = 0
    
    # Absolute path for Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'academy_combined_logo.png')
    
    context = {
        'student': request.user,
        'profile': profile,
        'transcript_data': transcript_data,
        'overall_avg': overall_avg,
        'date_issued': timezone.now(),
        'logo_path': logo_path if os.path.exists(logo_path) else None,
    }
    
    from utils.reports import render_to_pdf
    pdf = render_to_pdf('pdf/comprehensive_transcript.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Transcript_{request.user.username}_All_Courses.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)

# ============================================================================
# BULK OPERATIONS - Admin Dashboard Enhancements
# ============================================================================

@login_required
def bulk_approve_assignments(request):
    """Bulk approve multiple assignments at once or list them for review"""
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404("You are not authorized to perform this action.")
    
    if request.method == 'POST':
        assignment_ids = request.POST.getlist('assignment_ids')
        
        if not assignment_ids:
            messages.error(request, "No assignments selected.")
            return redirect('bulk-approve-assignments')
        
        # Approve all selected assignments
        approved_count = Assignment.objects.filter(
            id__in=assignment_ids,
            status='PENDING'
        ).update(status='APPROVED')
        
        messages.success(request, f"Successfully approved {approved_count} assignment(s).")
        return redirect('bulk-approve-assignments')
    
    # GET request - Show list of pending assignments
    pending_assignments = Assignment.objects.filter(
        status='PENDING'
    ).select_related('course', 'module', 'created_by').order_by('-created_at')
    
    return render(request, 'accounts/bulk_approve_assignments.html', {
        'pending_assignments': pending_assignments
    })

@login_required
def bulk_reject_assignments(request):
    """Bulk reject multiple assignments with a reason"""
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404("You are not authorized to perform this action.")
    
    if request.method == 'POST':
        assignment_ids = request.POST.getlist('assignment_ids')
        rejection_reason = request.POST.get('rejection_reason', 'No reason provided')
        
        if not assignment_ids:
            messages.error(request, "No assignments selected.")
            return redirect('admin-dashboard')
        
        if not rejection_reason.strip():
            messages.error(request, "Please provide a rejection reason.")
            return redirect('admin-dashboard')
        
        # Reject all selected assignments
        assignments = Assignment.objects.filter(
            id__in=assignment_ids,
            status='PENDING'
        )
        
        rejected_count = 0
        for assignment in assignments:
            assignment.status = 'REJECTED'
            assignment.rejection_reason = rejection_reason
            assignment.save()
            rejected_count += 1
        
        messages.success(request, f"Successfully rejected {rejected_count} assignment(s).")
        return redirect('admin-dashboard')
    
    return redirect('admin-dashboard')

@login_required
def bulk_approve_grades(request):
    """Bulk approve (lock) multiple grades at once"""
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404("You are not authorized to perform this action.")
    
    if request.method == 'POST':
        submission_ids = request.POST.getlist('submission_ids')
        
        if not submission_ids:
            messages.error(request, "No grades selected.")
            return redirect('admin-dashboard')
        
        submissions = Submission.objects.filter(id__in=submission_ids, is_marked=True).select_related('student', 'assignment')
        from utils.emails import send_mail_background
        for sub in submissions:
            if sub.student.email:
                subject = f"Grade Approved: {sub.assignment.title}"
                message = f"Dear {sub.student.username},\n\nYour grade for '{sub.assignment.title}' has been approved by the Admin and is now locked."
                send_mail_background(subject, message, [sub.student.email])
        
        # Lock all selected submissions
        locked_count = submissions.update(is_approved=True, is_locked=True)
        
        messages.success(request, f"Successfully locked {locked_count} grade(s) and sent notifications.")
        return redirect('admin-dashboard')
    
    return redirect('admin-dashboard')

@login_required
def download_certificate(request, course_id):
    if not request.user.role == 'STUDENT':
        raise Http404("Only students can download certificates.")
        
    course = get_object_or_404(Course, id=course_id)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
         
    # --- Lock Override Logic ---
    override = enrollment.certificate_lock_override
    if override == 'LOCKED':
        messages.error(request, "Certificate is locked by Admin.")
        return redirect('student-dashboard')
    elif override == 'UNLOCKED':
        # Skip all rules
        pass
    else:
        # Check if course is completed
        # Assignment totals per course
        total_assignments = Assignment.objects.filter(course=course, status='APPROVED').count()
        graded_submissions = Submission.objects.filter(student=request.user, assignment__course=course, is_marked=True)
        graded_count = graded_submissions.count()
        avg_mark = graded_submissions.aggregate(Avg('percentage'))['percentage__avg'] or 0
        
        all_graded = (total_assignments == graded_count) if total_assignments > 0 else False
        has_passing_grade = avg_mark >= 50
        
        if not all_graded:
            messages.error(request, f"Certificate locked. Complete all assignments ({graded_count}/{total_assignments} graded).")
            return redirect('student-dashboard')
        if not has_passing_grade:
            messages.error(request, f"Certificate locked. Achieve a passing grade (current: {avg_mark:.1f}%).")
            return redirect('student-dashboard')

        # Check for Fee Clearance
        total_paid = FeePayment.objects.filter(
            student=request.user, 
            course=course, 
            status='APPROVED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        balance = course.fee - total_paid
        if balance > 0:
            messages.error(request, f"Certificate locked. Outstanding fee balance: KES {balance:,.2f}.")
            return redirect('view-fees')
    # --- End Lock Logic ---

    # Temporarily bypassed for preview
    pass
        
    # Data for the new certificate design
    student_full_name = request.user.get_full_name().strip() or request.user.username
    reg_no = getattr(request.user.studentprofile, 'registration_number', "N/A") if hasattr(request.user, 'studentprofile') else "N/A"
    
    # Certificate Numbering Logic: CU-CS-[COURSE_CODE]-[YEAR]-[STUDENT_ID_PADDED]
    import re as _re
    course_slug = "".join(_re.findall(r'[a-zA-Z0-9]+', course.name)).upper()
    issue_date = datetime.date.today()
    cert_no = f"CU-CS-{course_slug}-{issue_date.year}-{request.user.id:03d}"
    
    cohort = course.cohort
    start_date = cohort.start_date if cohort else None
    end_date = cohort.end_date if cohort else None

    context = {
        'student': request.user,
        'student_name': student_full_name,
        'registration_number': reg_no,
        'course': course,
        'cert_no': cert_no,
        'issue_date': issue_date,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    # If a manual certificate is uploaded, serve it directly (as a PDF)
    import os
    from io import BytesIO
    from PIL import Image

    if enrollment.manual_certificate:
        file_path = enrollment.manual_certificate.path
        if os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            
            # If it's already a PDF, serve it normally
            if ext == '.pdf':
                with open(file_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/pdf')
                    filename = f"Certificate_{request.user.username}.pdf"
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
            
            # If it's an image, CONVERT to PDF
            elif ext in ['.jpg', '.jpeg', '.png']:
                try:
                    img = Image.open(file_path)
                    # Convert to RGB if it's RGBA (for PNGs)
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                    
                    pdf_io = BytesIO()
                    img.save(pdf_io, "PDF", resolution=100.0)
                    pdf_io.seek(0)
                    
                    response = HttpResponse(pdf_io.read(), content_type='application/pdf')
                    filename = f"Certificate_{request.user.username}.pdf"
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                except Exception as e:
                    print(f"Error converting image to PDF: {str(e)}")
                    # Fallback: serve original image if conversion fails
                    with open(file_path, 'rb') as f:
                        import mimetypes
                        content_type = mimetypes.guess_type(file_path)[0] or 'image/jpeg'
                        response = HttpResponse(f.read(), content_type=content_type)
                        filename = f"Certificate_{request.user.username}{ext}"
                        response['Content-Disposition'] = f'attachment; filename="{filename}"'
                        return response

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

        # Notify Admins
        from django.core.mail import send_mail
        from django.conf import settings
        admins = User.objects.filter(Q(role='ADMIN') | Q(is_superuser=True)).distinct()
        admin_emails = [a.email for a in admins if a.email]
        if admin_emails:
            subject = f"New Payment Verification Needed: {transaction_id}"
            message = f"Student {request.user.username} has submitted a {provider} payment of {amount} KES (ID: {transaction_id}) for verification."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=False)

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

        # Notify Admins
        from django.core.mail import send_mail
        from django.conf import settings
        admins = User.objects.filter(Q(role='ADMIN') | Q(is_superuser=True)).distinct()
        admin_emails = [a.email for a in admins if a.email]
        if admin_emails:
            subject = f"New Bank Payment Verification Needed: {transaction_id}"
            message = f"Student {request.user.username} has submitted a Bank payment of {amount} KES (ID: {transaction_id}) via {bank_name} for verification."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=False)

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
        
        if action in ['approve', 'reject']:
            if action == 'approve':
                payment.status = 'APPROVED'
            else:
                payment.status = 'REJECTED'
                payment.remarks = request.POST.get('remarks', 'Rejected by admin')
            payment.save()
            
            # Notify Student
            from django.core.mail import send_mail
            from django.conf import settings
            if payment.student.email:
                subject = f"Payment {payment.status}: {payment.transaction_id}"
                if action == 'approve':
                    message = f"Dear {payment.student.username},\n\nYour payment of {payment.amount} KES (ID: {payment.transaction_id}) for {payment.course.name} has been approved."
                else:
                    message = f"Dear {payment.student.username},\n\nYour payment of {payment.amount} KES (ID: {payment.transaction_id}) for {payment.course.name} has been rejected.\nRemarks: {payment.remarks}"
                
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [payment.student.email], fail_silently=False)

            if action == 'reject':
                messages.warning(request, f"Rejected payment {payment.transaction_id}")
            else:
                messages.success(request, f"Approved payment {payment.transaction_id}")
            
        return redirect('verify-payments')
        
    # List pending view
    payments = FeePayment.objects.filter(status='PENDING').order_by('-payment_date')
    return render(request, 'accounts/verify_payments.html', {'payments': payments})

# --- Reporting Views ---

@login_required
def generate_enrollment_report(request):
    if not request.user.role in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
        
    enrollments = Enrollment.objects.filter(student__role='STUDENT').select_related('student', 'student__studentprofile', 'course', 'cohort').order_by('-enrolled_at')
    
    if 'pdf' in request.GET:
        filename = f"Enrollment_Report_{datetime.date.today()}.pdf"
        return render_to_pdf('reports/enrollment_report.html', {'enrollments': enrollments, 'date': datetime.date.today()}, filename=filename)
        
    return export_to_csv(
        enrollments, 
        'enrollment_report', 
        ['student.studentprofile.registration_number', 'student.get_full_name', 'student.email', 'course.name', 'cohort.name', 'enrolled_at'],
        ['Reg No', 'Full Name', 'Email', 'Course', 'Cohort', 'Enrolled Date']
    )

@login_required
def generate_payment_report(request):
    if not request.user.role in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
        
    from courses.models import Enrollment, FeePayment
    import datetime

    from courses.models import FeePayment
    
    payments = FeePayment.objects.select_related(
        'student', 'student__studentprofile', 'course'
    ).order_by('-payment_date')

    if 'pdf' in request.GET:
        filename = f"Fee_Payment_Report_{datetime.date.today()}.pdf"
        return render_to_pdf('reports/payment_report.html', {'payments': payments, 'date': datetime.date.today()}, filename=filename)
        
    return export_to_csv(
        payments, 
        'fee_payment_report', 
        ['payment_date', 'student.get_full_name', 'student.studentprofile.registration_number', 'course.name', 'amount', 'payment_method', 'provider', 'transaction_id', 'status'],
        ['Date', 'Student Name', 'Admin No', 'Course', 'Amount', 'Method', 'Medium', 'Reference', 'Status']
    )

@login_required
def generate_fee_balance_report(request):
    if not request.user.role in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
        
    from courses.models import Enrollment, FeePayment
    import datetime
    
    enrollments = Enrollment.objects.filter(student__role='STUDENT').select_related(
        'student', 'student__studentprofile', 'course', 'cohort'
    ).order_by('-enrolled_at')
    
    report_data = []
    
    # Optimization: fetch non-rejected payments
    all_payments = FeePayment.objects.exclude(status='REJECTED').select_related('student', 'course')
    from collections import defaultdict
    payments_by_enrollment_approved = defaultdict(float)
    payments_by_enrollment_pending = defaultdict(float)
    
    for p in all_payments:
        if p.status == 'APPROVED':
            payments_by_enrollment_approved[(p.student_id, p.course_id)] += float(p.amount)
        elif p.status == 'PENDING':
            payments_by_enrollment_pending[(p.student_id, p.course_id)] += float(p.amount)
        
    for enrollment in enrollments:
        course_fee = float(enrollment.course.fee)
        total_paid = payments_by_enrollment_approved.get((enrollment.student_id, enrollment.course_id), 0.0)
        pending_amount = payments_by_enrollment_pending.get((enrollment.student_id, enrollment.course_id), 0.0)
        balance = course_fee - total_paid
        
        if balance <= 0:
            status = "CLEARED"
        elif pending_amount > 0:
            status = "PENDING VERIFICATION"
        else:
            status = "PARTIAL" if total_paid > 0 else "UNPAID"
        
        profile = getattr(enrollment.student, 'studentprofile', None)
        reg_no = profile.registration_number if profile else 'N/A'
        
        report_data.append({
            'enrollment': enrollment,
            'reg_no': reg_no,
            'course_fee': course_fee,
            'total_paid': total_paid,
            'pending_amount': pending_amount,
            'balance': balance,
            'status': status
        })
    
    if 'pdf' in request.GET:
        filename = f"Fee_Balance_Report_{datetime.date.today()}.pdf"
        return render_to_pdf('reports/fee_balance_report.html', {'report_data': report_data, 'date': datetime.date.today()}, filename=filename)
        
    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="fee_balance_report_{datetime.date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Reg No', 'Student Name', 'Course', 'Cohort', 'Course Fee', 'Total Paid', 'Pending Verification', 'Balance', 'Status'])
    
    for item in report_data:
        student = item['enrollment'].student
        writer.writerow([
            item['reg_no'],
            student.get_full_name() or student.username,
            item['enrollment'].course.name,
            item['enrollment'].cohort.name if item['enrollment'].cohort else 'N/A',
            item['course_fee'],
            item['total_paid'],
            item['pending_amount'],
            item['balance'],
            item['status']
        ])
        
    return response

@login_required
def generate_student_progress_report(request):
    if not request.user.role in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
        
    from courses.models import Cohort, Enrollment
    from assignments.models import Assignment, AssignmentAvailability
    from submissions.models import Submission
    import datetime
    
    enrollments = Enrollment.objects.filter(student__role='STUDENT').select_related(
        'student', 'student__studentprofile', 'course', 'cohort'
    ).order_by('cohort__name', 'student__username')
    
    report_data = []
    
    # Precompute total assignments per cohort
    from collections import defaultdict
    assignments_per_cohort = defaultdict(int)
    availabilities = AssignmentAvailability.objects.filter(assignment__status='APPROVED').select_related('cohort')
    for avail in availabilities:
        assignments_per_cohort[avail.cohort_id] += 1
        
    assignment_cohorts = defaultdict(list)
    for avail in availabilities:
        assignment_cohorts[avail.assignment_id].append(avail.cohort_id)
        
    # Precompute submissions per student + cohort combination
    submissions = Submission.objects.filter(
        assignment__status='APPROVED',
    ).select_related('student', 'assignment')
    
    student_cohort_submissions = defaultdict(set)
    for sub in submissions:
        cohorts = assignment_cohorts.get(sub.assignment_id, [])
        for cohort_id in cohorts:
            student_cohort_submissions[(sub.student_id, cohort_id)].add(sub.assignment_id)
            
    for enrollment in enrollments:
        student = enrollment.student
        cohort = enrollment.cohort
        
        if not cohort:
            continue
            
        total_assignments = assignments_per_cohort.get(cohort.id, 0)
        submitted_assignments = len(student_cohort_submissions.get((student.id, cohort.id), set()))
        not_submitted = total_assignments - submitted_assignments
        
        progress_percent = (submitted_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        profile = getattr(student, 'studentprofile', None)
        reg_no = profile.registration_number if profile else 'N/A'
        
        report_data.append({
            'enrollment': enrollment,
            'reg_no': reg_no,
            'total_assignments': total_assignments,
            'submitted': submitted_assignments,
            'not_submitted': not_submitted,
            'progress_percent': progress_percent
        })
        
    if 'pdf' in request.GET:
        filename = f"Student_Progress_Report_{datetime.date.today()}.pdf"
        return render_to_pdf('reports/student_progress_report.html', {'report_data': report_data, 'date': datetime.date.today()}, filename=filename)
        
    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="student_progress_report_{datetime.date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Reg No', 'Student Name', 'Course', 'Cohort', 'Total Assignments', 'Submitted', 'Not Submitted', 'Progress %'])
    
    for item in report_data:
        student = item['enrollment'].student
        writer.writerow([
            item['reg_no'],
            student.get_full_name() or student.username,
            item['enrollment'].course.name,
            item['enrollment'].cohort.name,
            item['total_assignments'],
            item['submitted'],
            item['not_submitted'],
            f"{item['progress_percent']:.1f}%"
        ])
        
    return response
@login_required
def download_fee_structure(request):
    from courses.models import Course
    courses = Course.objects.all().select_related('cohort').order_by('name')
    filename = f"Fee_Structure_{datetime.date.today()}.pdf"
    return render_to_pdf('pdf/fee_structure.html', {
        'courses': courses,
        'date': datetime.date.today()
    }, filename=filename)


@login_required
def toggle_grade_lock(request, submission_id):
    if not request.user.role in ['ADMIN', 'SUPERADMIN'] and not request.user.is_superuser:
        raise Http404()
    
    submission = get_object_or_404(Submission, id=submission_id)
    submission.is_locked = not submission.is_locked
    if not submission.is_locked:
        submission.is_marked = False
        submission.marks_awarded = None
    submission.save()
    
    status = "locked" if submission.is_locked else "unlocked"
    messages.success(request, f"Successfully {status} grades for {submission.student.username}.")
    return redirect('admin-dashboard')

@login_required
def lecturer_student_list(request):
    if not request.user.is_superuser and request.user.role != 'LECTURER':
        raise Http404("You are not authorized to view this page.")
    
    from courses.models import Cohort, Enrollment
    from assignments.models import Assignment, AssignmentAvailability
    from submissions.models import Submission

    current_filter = request.GET.get('filter', 'all')

    # Get cohorts assigned to this lecturer
    if request.user.is_superuser:
        assigned_cohorts = Cohort.objects.filter(is_active=True)
    else:
        assigned_cohorts = request.user.assigned_cohorts.all()

    # Get all enrollments for these cohorts, filtering for students only
    enrollments = Enrollment.objects.filter(
        cohort__in=assigned_cohorts,
        student__role='STUDENT'
    ).select_related('student', 'cohort', 'course').order_by('cohort__name', 'student__username')

    student_data = []
    for enrollment in enrollments:
        student = enrollment.student
        cohort = enrollment.cohort
        
        # Get count of approved assignments for this cohort
        total_assignments = AssignmentAvailability.objects.filter(cohort=cohort, assignment__status='APPROVED').count()
        
        # Get count of submissions by this student for assignments in this cohort
        submitted_count = Submission.objects.filter(
            student=student, 
            assignment__availabilities__cohort=cohort,
            assignment__status='APPROVED'
        ).distinct().count()

        # Get count of marked submissions
        marked_count = Submission.objects.filter(
            student=student, 
            assignment__availabilities__cohort=cohort,
            assignment__status='APPROVED',
            is_marked=True
        ).distinct().count()

        pending_count = submitted_count - marked_count

        if current_filter == 'pending' and pending_count == 0:
            continue

        student_data.append({
            'student': student,
            'cohort': cohort,
            'total': total_assignments,
            'submitted': submitted_count,
            'marked': marked_count,
            'pending': pending_count,
            'progress_percent': (submitted_count / total_assignments * 100) if total_assignments > 0 else 0
        })

    # --- Limit / per-page control ---
    VALID_LIMITS = [15, 30, 50, 100, 150]
    try:
        limit = int(request.GET.get('limit', 15))
    except (ValueError, TypeError):
        limit = 15
    if limit not in VALID_LIMITS:
        limit = 15

    total_count = len(student_data)
    student_data = student_data[:limit]

    return render(request, 'lecturer_student_list.html', {
        'student_data': student_data,
        'current_filter': current_filter,
        'selected_limit': limit,
        'total_count': total_count,
        'valid_limits': VALID_LIMITS,
    })

# --- Custom Error Handlers ---
def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    import traceback
    import sys
    
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    context = {}
    if request.user.is_authenticated and request.user.is_superuser:
        if exc_type:
            context['exception_type'] = exc_type.__name__
            context['traceback'] = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    return render(request, '500.html', context, status=500)
