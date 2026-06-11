
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from assignments.models import Assignment, AssignmentAvailability
from submissions.models import Submission
from courses.models import Course, Cohort, Enrollment
from django.utils import timezone

User = get_user_model()

def test_delete_logic():
    print("Testing delete logic...")
    
    # 1. Setup Data
    user = User.objects.filter(username='teststudent').first()
    if not user:
        user = User.objects.create_user(username='teststudent', password='password', role='STUDENT')
    
    cohort = Cohort.objects.first()
    if not cohort:
        cohort = Cohort.objects.create(name='Test Cohort')
    
    course = Course.objects.first()
    if not course:
        course = Course.objects.create(name='Test Course', cohort=cohort)
    
    assignment = Assignment.objects.first()
    if not assignment:
        assignment = Assignment.objects.create(title='Test Assignment', course=course, status='APPROVED')
    
    submission = Submission.objects.create(student=user, assignment=assignment)
    
    print(f"Created submission: {submission.id}")
    
    try:
        # Simulate accounts/views.py delete_submission
        print("Attempting to delete and access assignment.id...")
        # In the view:
        # submission.delete()
        # return redirect('submit-assignment', assignment_id=submission.assignment.id)
        
        # We'll save assignment_id before delete to see if it makes a difference
        # but let's try EXACTLY as in code first
        
        # We need to make sure assignment is NOT pre-fetched to be safe
        submission = Submission.objects.get(id=submission.id)
        
        print("Deleting submission...")
        submission.delete()
        print("Deletion successful.")
        
        print("Accessing submission.assignment.id...")
        aid = submission.assignment.id
        print(f"Assignment ID: {aid}")
        
    except Exception as e:
        print(f"FAILED: Accessing assignment.id after delete raised: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_delete_logic()
