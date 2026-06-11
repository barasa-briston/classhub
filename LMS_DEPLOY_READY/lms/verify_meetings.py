
import os
import django
import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Cohort, OnlineMeeting, Enrollment, Course
from django.contrib.auth import get_user_model

User = get_user_model()

def verify():
    print("--- Verifying Online Meetings System ---")
    
    # 1. Setup Test Data
    lecturer = User.objects.filter(role='LECTURER').first()
    if not lecturer:
        print("Error: No lecturer found.")
        return
    
    student = User.objects.filter(role='STUDENT').first()
    if not student:
        print("Error: No student found.")
        return
        
    cohort = Cohort.objects.first()
    if not cohort:
        print("Error: No cohort found.")
        return
        
    # Ensure lecturer is assigned to cohort
    cohort.lecturers.add(lecturer)
    
    course = Course.objects.first()
    if not course:
        print("Error: No course found.")
        return
        
    # Ensure student is enrolled
    Enrollment.objects.get_or_create(student=student, course=course, defaults={'cohort': cohort})
    
    # 2. Create Meeting
    topic = f"Test Meeting {timezone.now().timestamp()}"
    meeting = OnlineMeeting.objects.create(
        cohort=cohort,
        topic=topic,
        meeting_date=timezone.now() + datetime.timedelta(hours=1),
        meeting_link="https://conference.ke/test",
        meeting_password="123",
        created_by=lecturer
    )
    print(f"Success: Created meeting '{topic}'")
    
    # 3. Verify Student Access
    # Query like the student view does
    enrollments = Enrollment.objects.filter(student=student)
    cohort_ids = enrollments.values_list('cohort_id', flat=True)
    visible_meetings = OnlineMeeting.objects.filter(cohort_id__in=cohort_ids, topic=topic)
    
    if visible_meetings.exists():
        print(f"Success: Student can see meeting '{topic}'")
    else:
        print(f"Error: Student cannot see meeting.")
        
    # 4. Verify Recording Delay Logic
    # Shared now, but meeting was 48 hours ago
    past_meeting = OnlineMeeting.objects.create(
        cohort=cohort,
        topic="Past Meeting",
        meeting_date=timezone.now() - datetime.timedelta(hours=48),
        meeting_link="https://old",
        recording_shared_at=timezone.now()
    )
    
    if past_meeting.is_recording_available:
        print("Success: Recording correctly identified as available (past 24h).")
    else:
        print("Error: Recording logic failed for past meeting.")
        
    # Shared now, but meeting was 5 hours ago
    recent_meeting = OnlineMeeting.objects.create(
        cohort=cohort,
        topic="Recent Meeting",
        meeting_date=timezone.now() - datetime.timedelta(hours=5),
        meeting_link="https://recent",
        recording_shared_at=timezone.now()
    )
    
    if not recent_meeting.is_recording_available:
        print("Success: Recording correctly identified as NOT available yet (within 24h).")
    else:
        print("Error: Recording logic failed for recent meeting (available too early).")

    # Cleanup
    meeting.delete()
    past_meeting.delete()
    recent_meeting.delete()
    print("--- Verification Complete ---")

if __name__ == "__main__":
    verify()
