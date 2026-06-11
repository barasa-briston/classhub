from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import OnlineMeeting, Cohort, Enrollment, AttendanceRecord
from .forms import MeetingForm, RecordingForm, EditMeetingForm
from django.http import Http404
from django.db import models

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
def meeting_attendance_list(request, meeting_id):
    meeting = get_object_or_404(OnlineMeeting, id=meeting_id)
    if request.user.role == 'STUDENT':
         raise Http404()
    
    # Check if lecturer has access to this cohort
    if request.user.role == 'LECTURER':
         if not meeting.cohort.lecturers.filter(id=request.user.id).exists():
              raise Http404()

    records = AttendanceRecord.objects.filter(meeting=meeting, is_attended=True).select_related('student')
    
    context = {
        'meeting': meeting,
        'records': records,
    }
    return render(request, 'courses/meeting_attendance.html', context)

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
    
    # Pre-fetch all attendance records for this cohort and these students in 1 query
    student_ids = [e.student_id for e in enrollments]
    attendance_lookup = AttendanceRecord.objects.filter(
        student_id__in=student_ids,
        meeting__cohort=cohort,
        is_attended=True
    ).values('student_id').annotate(count=models.Count('id'))
    
    attended_map = {item['student_id']: item['count'] for item in attendance_lookup}
    
    # Only count meetings that have reached their scheduled time
    total_meetings = OnlineMeeting.objects.filter(
        cohort=cohort,
        meeting_date__lte=timezone.now()
    ).count()
    
    students_data = []
    for enrollment in enrollments:
        student = enrollment.student
        attended_count = attended_map.get(student.id, 0)
        
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

@login_required
def edit_meeting(request, meeting_id):
    if request.user.role != 'LECTURER' and not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
    
    meeting = get_object_or_404(OnlineMeeting, id=meeting_id)
    
    # Check permission (Lecturer must belong to cohort)
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        if request.user not in meeting.cohort.lecturers.all():
            raise Http404("You are not the lecturer for this cohort.")
            
    if request.method == 'POST':
        form = EditMeetingForm(request.POST, instance=meeting, lecturer=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Meeting '{meeting.topic}' updated successfully.")
            return redirect('manage-meetings')
    else:
        form = EditMeetingForm(instance=meeting, lecturer=request.user)
    
    return render(request, 'meetings/edit.html', {
        'form': form,
        'meeting': meeting
    })

@login_required
def delete_meeting(request, meeting_id):
    if request.user.role != 'LECTURER' and not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        raise Http404()
    
    meeting = get_object_or_404(OnlineMeeting, id=meeting_id)
    
    # Check permission
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'SUPERADMIN']:
        if request.user not in meeting.cohort.lecturers.all():
            raise Http404("You are not the lecturer for this cohort.")
            
    if request.method == 'POST':
        topic = meeting.topic
        meeting.delete()
        messages.success(request, f"Meeting '{topic}' deleted successfully.")
        return redirect('manage-meetings')
        
    return redirect('manage-meetings')


@login_required
def upload_resource(request):
    """Allow lecturers and admins to upload study resources (notes, PDFs, links)."""
    if request.user.role not in ['LECTURER', 'ADMIN', 'SUPERADMIN'] and not request.user.is_superuser:
        raise Http404("Only lecturers and admins can upload resources.")

    if request.method == 'POST':
        from .models import Resource
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        icon_class = request.POST.get('icon_class', 'fa-file-pdf').strip()
        external_url = request.POST.get('external_url', '').strip()
        order = request.POST.get('order', '0')
        uploaded_file = request.FILES.get('file')

        if not title:
            messages.error(request, "A title is required.")
            return redirect('lecturer-dashboard')

        if not uploaded_file and not external_url:
            messages.error(request, "Please upload a file or provide an external URL.")
            return redirect('lecturer-dashboard')

        try:
            order = int(order)
        except ValueError:
            order = 0

        resource = Resource(
            title=title,
            description=description,
            icon_class=icon_class or 'fa-file-pdf',
            order=order,
            is_active=True,
        )
        if uploaded_file:
            resource.file = uploaded_file
        if external_url:
            resource.external_url = external_url
        resource.save()
        messages.success(request, f"Resource '{title}' uploaded successfully!")

    return redirect('lecturer-dashboard')


@login_required
def delete_resource(request, resource_id):
    """Allow lecturers and admins to delete a resource."""
    if request.user.role not in ['LECTURER', 'ADMIN', 'SUPERADMIN'] and not request.user.is_superuser:
        raise Http404()

    if request.method == 'POST':
        from .models import Resource
        resource = get_object_or_404(Resource, id=resource_id)
        title = resource.title
        # Delete the actual file from storage if it exists
        if resource.file:
            resource.file.delete(save=False)
        resource.delete()
        messages.success(request, f"Resource '{title}' deleted.")

    return redirect('lecturer-dashboard')

