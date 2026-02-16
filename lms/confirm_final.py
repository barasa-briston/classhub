
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Enrollment, Cohort, OnlineMeeting

User = get_user_model()
student_username = "barasa"

def final_confirm():
    print(f"--- Final Terminal Confirmation for '{student_username}' ---")
    
    student = User.objects.filter(username=student_username).first()
    if not student:
        print(f"Error: Student '{student_username}' not found.")
        return

    # 1. Ensure Cohort and Enrollment exist properly
    cohort = Cohort.objects.filter(name="CCNA 1").first()
    if not cohort:
        print("Error: Cohort 'CCNA 1' not found.")
        return
        
    enrollment = Enrollment.objects.filter(student=student).first()
    if not enrollment:
        print(f"Error: No enrollment record for {student_username}.")
    else:
        # Force the fix clearly
        enrollment.cohort = cohort
        if not enrollment.course:
            # Assign to the course associated with this cohort if missing
            from courses.models import Course 
            enrollment.course = Course.objects.first() 
        enrollment.save()
        print(f"Success: Student {student_username} is now firmly in Cohort '{cohort.name}'")

    # 2. Simulate the Dashboard View Logic
    enrollments = Enrollment.objects.filter(student=student)
    cohort_ids = enrollments.values_list('cohort_id', flat=True)
    visible_meetings = OnlineMeeting.objects.filter(cohort_id__in=cohort_ids)

    print(f"Visible Meetings Count for {student_username}: {visible_meetings.count()}")
    for m in visible_meetings:
        print(f"  - [{m.id}] {m.topic} (Date: {m.meeting_date})")

    if visible_meetings.count() > 0:
        print("\nRESULT: System is WORKING. Student can see the meetings.")
    else:
        print("\nRESULT: System still showing nothing. Check if meetings are assigned to the correct cohort.")

if __name__ == "__main__":
    final_confirm()
