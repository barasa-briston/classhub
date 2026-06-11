
import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import OnlineMeeting, Enrollment, Cohort

User = get_user_model()
student_name = "barasa"
student = User.objects.filter(username=student_name).first()

with open('debug_output.txt', 'w') as f:
    if not student:
        f.write(f"Student '{student_name}' not found.\n")
    else:
        f.write(f"Student: {student.username} (Role: {student.role})\n")
        enrollments = Enrollment.objects.filter(student=student)
        f.write(f"Enrollments count: {enrollments.count()}\n")
        for en in enrollments:
            cohort = en.cohort
            if not cohort:
                f.write(f"  Enrollment {en.id} has NO COHORT!\n")
                continue
            f.write(f"  Enrolled in Cohort: {cohort.id} - {cohort.name}\n")
            meetings = OnlineMeeting.objects.filter(cohort=cohort)
            f.write(f"    Meetings for this cohort: {meetings.count()}\n")
            for m in meetings:
                f.write(f"      - Topic: {m.topic}, Date: {m.meeting_date}\n")

    total_meetings = OnlineMeeting.objects.count()
    f.write(f"\nTotal Meetings in DB: {total_meetings}\n")
    if total_meetings > 0:
        for m in OnlineMeeting.objects.all():
            m_cohort = m.cohort.name if m.cohort else "NONE"
            f.write(f"  - [{m.id}] Topic: {m.topic} | Cohort: {m_cohort} | Date: {m.meeting_date}\n")
    else:
        f.write("  No meetings found in database.\n")
