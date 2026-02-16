from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import OnlineMeeting, Cohort, Enrollment, AttendanceRecord
from .forms import MeetingForm, RecordingForm
from django.http import Http404

@login_required
def track_attendance(request, meeting_id):
    meeting = get_object_or_404(OnlineMeeting, id=meeting_id)
    if request.user.role == 'STUDENT':
        # Create or get record
        record, created = AttendanceRecord.objects.get_or_create(
            meeting=meeting,
            student=request.user
        )
        # Mark as attended only if joined timely (within first 30 mins)
        if meeting.is_punctual(timezone.now()):
            record.is_attended = True 
            status_msg = f"Attendance recorded for {meeting.topic}."
        else:
            record.is_attended = False
            status_msg = f"Joined {meeting.topic}, but attendance not marked (late join)."
            
        record.save()
        
        # Calculate new percentage for notification
        total = OnlineMeeting.objects.filter(cohort=meeting.cohort, meeting_date__lte=timezone.now()).count()
        attended = AttendanceRecord.objects.filter(student=request.user, meeting__cohort=meeting.cohort, is_attended=True).count()
        percentage = (attended / total * 100) if total > 0 else 0
        messages.info(request, f"{status_msg} Your current participation is {round(percentage, 1)}%.")
        
    return redirect(meeting.meeting_link)

@login_required
def manage_meetings(request):
    if request.user.role != 'LECTURER' and not request.user.is_superuser:
        if request.user.role in ['ADMIN', 'SUPERADMIN'] or request.user.is_superuser:
            pass # Admins can manage too
        else:
            raise Http404("Only Lecturers and Admins can manage meetings.")
    
    # Filter cohorts for the lecturer/admin
    if request.user.is_superuser or request.user.role in ['ADMIN', 'SUPERADMIN']:
        eligible_cohorts = Cohort.objects.all()
    else:
        eligible_cohorts = Cohort.objects.filter(lecturers=request.user)
        
    meetings = OnlineMeeting.objects.filter(cohort__in=eligible_cohorts).order_by('-meeting_date')
    
    if request.method == 'POST':
        form = MeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.created_by = request.user
            meeting.save()
            messages.success(request, f"Meeting '{meeting.topic}' scheduled successfully.")
            return redirect('manage-meetings')
    else:
        form = MeetingForm()
        # Limit cohort choices to eligible ones
        form.fields['cohort'].queryset = eligible_cohorts
    
    return render(request, 'meetings/manage.html', {
        'meetings': meetings,
        'form': form
    })

@login_required
def upload_recording(request, meeting_id):
    if request.user.role != 'LECTURER' and not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
    
    meeting = get_object_or_404(OnlineMeeting, id=meeting_id)
    # Check permission
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        if request.user not in meeting.cohort.lecturers.all():
            raise Http404("You are not the lecturer for this cohort.")
    
    if request.method == 'POST':
        form = RecordingForm(request.POST, request.FILES, instance=meeting)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.recording_shared_at = timezone.now()
            rec.save()
            
            # Notification logic (simplified)
            students = meeting.cohort.students.all()
            # In a real app, send bulk email here
            
            messages.success(request, f"Recording for '{meeting.topic}' has been shared with students.")
            return redirect('manage-meetings')
    else:
        form = RecordingForm(instance=meeting)
    
    return render(request, 'meetings/upload_recording.html', {'meeting': meeting, 'form': form})

@login_required
def student_meetings(request):
    if request.user.role != 'STUDENT':
        raise Http404()
    
    # Get cohorts via Enrollment
    enrollments = Enrollment.objects.filter(student=request.user)
    cohort_ids = enrollments.values_list('cohort_id', flat=True)
    
    meetings = OnlineMeeting.objects.filter(cohort_id__in=cohort_ids).order_by('-meeting_date')
    
    return render(request, 'meetings/student_list.html', {
        'meetings': meetings,
        'now': timezone.now()
    })

@login_required
def attendance_report(request, cohort_id):
    if request.user.role != 'LECTURER' and not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    # Get all students in this cohort
    enrollments = Enrollment.objects.filter(cohort=cohort).select_related('student')
    students_data = []
    
    # Only count meetings that have reached their scheduled time
    total_meetings = OnlineMeeting.objects.filter(
        cohort=cohort,
        meeting_date__lte=timezone.now()
    ).count()
    
    for enrollment in enrollments:
        student = enrollment.student
        attended_count = AttendanceRecord.objects.filter(
            student=student, 
            meeting__cohort=cohort,
            is_attended=True
        ).count()
        
        percentage = (attended_count / total_meetings * 100) if total_meetings > 0 else 0
        students_data.append({
            'student': student,
            'attended': attended_count,
            'missed': max(0, total_meetings - attended_count),
            'percentage': round(percentage, 1),
            'has_perfect_attendance': attended_count >= total_meetings and total_meetings > 0
        })
        
    return render(request, 'meetings/attendance_report.html', {
        'cohort': cohort,
        'total_meetings': total_meetings,
        'students_data': students_data
    })
