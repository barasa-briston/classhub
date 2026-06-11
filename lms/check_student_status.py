
import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from assignments.models import Assignment, AssignmentAvailability
from submissions.models import Submission

User = get_user_model()
username = 'snjoroge'

try:
    student = User.objects.get(username=username)
    print(f"Checking status for student: {student.username}")
except User.DoesNotExist:
    print(f"User {username} not found. Listing first 5 students...")
    for u in User.objects.filter(role='STUDENT')[:5]:
        print(f" - {u.username}")
    exit()

submissions = Submission.objects.filter(student=student)

if not submissions.exists():
    print("No submissions found for this student.")
else:
    with open('student_status.txt', 'w') as f:
        for sub in submissions:
            f.write(f"\n--- Assignment: {sub.assignment.title} (ID: {sub.assignment.id}) ---\n")
            
            # Check availability/deadline
            avail = AssignmentAvailability.objects.filter(
                assignment=sub.assignment, 
                cohort__courses__enrollments__student=student
            ).first()
            
            now = timezone.now()
            # Handle the case where availability might be None (though unlikely if enrolled correctly)
            if avail:
                eff_dead = avail.deadline
                allow_late = avail.allow_late
                late_until = avail.late_until
            else:
                 eff_dead = None # Or assignment.deadline if it still existed, but it doesn't
                 allow_late = False
                 late_until = None

            f.write(f"  Current Time: {now}\n")
            f.write(f"  Deadline    : {eff_dead}\n")
            
            is_late = False
            if eff_dead and now > eff_dead:
                is_late = True
            
            f.write(f"  Is Late?    : {is_late}\n")
            f.write(f"  Allow Late? : {allow_late}\n")
            
            f.write(f"  Submission Locked? : {sub.is_locked}\n")
            f.write(f"  Submission Marked? : {sub.is_marked}\n")
            
            # Logic from view
            can_delete = True
            reason = "OK"
            
            if sub.is_marked or sub.is_locked:
                can_delete = False
                reason = "LOCKED/MARKED"
            elif is_late:
                if not allow_late:
                     can_delete = False
                     reason = "DEADLINE PASSED (Late not allowed)"
                elif late_until and now > late_until:
                     can_delete = False
                     reason = "LATE DEADLINE PASSED"
            
            f.write(f"  >>> CAN SEE DELETE BUTTON? : {can_delete}\n")
            if not can_delete:
                f.write(f"      Reason: {reason}\n")
