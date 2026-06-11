
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from assignments.models import Assignment, AssignmentAvailability
from submissions.models import Submission, SubmissionFile
from courses.models import Course, Cohort, Enrollment
from django.utils import timezone
from django.test import RequestFactory
from accounts.views import submit_assignment

User = get_user_model()

def verify_resubmission_logic():
    print("Verifying resubmission logic in accounts/views.py...")
    
    # 1. Setup Data
    username = 'resubmit_student'
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(username=username, password='password', role='STUDENT')
    
    cohort = Cohort.objects.first()
    course = Course.objects.filter(cohort=cohort).first()
    assignment = Assignment.objects.filter(course=course, status='APPROVED').first()
    
    if not assignment:
        print("No suitable assignment found for test.")
        return

    # Ensure enrollment
    Enrollment.objects.get_or_create(student=user, course=course, cohort=cohort)
    
    # Ensure availability
    AssignmentAvailability.objects.get_or_create(
        assignment=assignment, 
        cohort=cohort, 
        defaults={'deadline': timezone.now() + timezone.timedelta(days=1)}
    )

    # 2. Create an initial FAILED submission
    submission = Submission.objects.create(
        student=user, 
        assignment=assignment, 
        marks_awarded=10, # Fail
        is_marked=True,
        is_locked=False # Auto-unlocked because failed
    )
    SubmissionFile.objects.create(submission=submission, file='dummy.pdf')
    
    print(f"Initial submission {submission.id} created (Graded: F, Locked: False)")

    # 3. Simulate Student Resubmission (POST)
    factory = RequestFactory()
    
    # We need to simulate multiple files
    from django.core.files.uploadedfile import SimpleUploadedFile
    file1 = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
    file2 = SimpleUploadedFile("test.pka", b"content", content_type="application/octet-stream")
    file3 = SimpleUploadedFile("test.png", b"content", content_type="image/png")
    
    request = factory.post(f'/submit/{assignment.id}/', {
        'submission_files': [file1, file2, file3]
    })
    request.user = user
    # Add messages middleware mock
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(request, '_messages', FallbackStorage(request))

    print("Submitting new files...")
    response = submit_assignment(request, assignment.id)
    
    # 4. Verify results
    if response.status_code == 302:
        print("Redirected successfully.")
        
        # Check if submission was updated
        submission.refresh_from_db()
        print(f"Updated status: Marked={submission.is_marked}, Marks={submission.marks_awarded}, Files={submission.files.count()}")
        
        if submission.marks_awarded is None and submission.is_marked is False and submission.files.count() == 3:
            print("SUCCESS: Submission updated correctly for resubmission.")
        else:
            print("FAILURE: Submission not updated correctly.")
    else:
        print(f"FAILED: Response code {response.status_code}")
        if hasattr(response, 'context'):
             print("Context Errors:", response.context.get('reason'))

if __name__ == "__main__":
    verify_resubmission_logic()
