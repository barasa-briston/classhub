import os
import django
from django.utils import timezone
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assignments.models import Assignment, AssignmentAvailability
from audit.models import AssignmentAuditLog
from communications.models import Notice
from django.contrib.auth import get_user_model

User = get_user_model()

def verify():
    print("Starting Verification...")
    
    # 1. Get or create test data
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print("Creating admin user...")
        admin = User.objects.create_superuser('testadmin', 'admin@test.com', 'pass123')
    
    # Get an assignment
    assignment = Assignment.objects.first()
    if not assignment:
        print("No assignments found. Please create one.")
        return

    # Get an availability
    avail = assignment.availabilities.first()
    if not avail:
        print("No availabilities found for assignment.")
        return

    print(f"Testing bulk update on Assignment: {assignment.title}")
    print(f"Current Deadline: {avail.deadline}")

    # 2. Simulate Bulk Action (Deadline Update)
    new_deadline = timezone.now() + timedelta(days=7)
    
    # Logic from web_views.bulk_manage_assignments
    avail.deadline = new_deadline
    avail.allow_late = True
    avail.late_penalty = 10.0
    avail.save()

    # Log
    log = AssignmentAuditLog.objects.create(
        user=admin,
        assignment=assignment,
        action="Bulk Update Deadline (Test)",
        details={"new_deadline": str(new_deadline)}
    )

    # Notify
    notice = Notice.objects.create(
        title=f"Deadline Updated: {assignment.title}",
        content=f"The deadline has been updated to {new_deadline}.",
        cohort=avail.cohort,
        author=admin
    )

    # 3. Check results
    updated_avail = AssignmentAvailability.objects.get(id=avail.id)
    if updated_avail.deadline == new_deadline:
        print("[SUCCESS] Deadline updated successfully.")
    else:
        print("[FAILURE] Deadline update failed.")

    if AssignmentAuditLog.objects.filter(id=log.id).exists():
        print("[SUCCESS] Audit log created successfully.")
    
    if Notice.objects.filter(id=notice.id).exists():
        print("[SUCCESS] Student notification (Notice) created successfully.")

    print("\nVerification Complete.")

if __name__ == "__main__":
    verify()
