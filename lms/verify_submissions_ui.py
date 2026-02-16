import os
import django
import sys
import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import render_to_string
from django.conf import settings

# Mock classes
class MockCourse:
    name = "UI Design Course"

class MockAssignment:
    title = "Final Project"
    total_marks = 100
    course = MockCourse()

class MockSubmission:
    assignment = MockAssignment()
    submitted_at = datetime.datetime.now()
    is_marked = True
    grade = "A"
    marks_awarded = 95
    percentage = 95.0
    feedback = "Excellent work! " * 10
    is_approved = False

def verify_ui():
    print("--- Verifying Student Submissions UI Redesign (Template Only) ---")
    
    # 1. Setup Mock Data
    submissions = [MockSubmission()]
    
    # 2. Render Template Directly
    try:
        content = render_to_string('student_dashboard.html', {
            'submissions': submissions,
            'user': type('User', (object,), {'is_authenticated': True, 'username': 'test_student', 'role': 'STUDENT', 'is_superuser': False})(),
            'avg_mark': 95,
            'pass_status': 'PASS',
            'enrollments': [],
            'available_assignments': [],
            'all_over': False
        })
    except Exception as e:
         print(f"FAIL: Template rendering failed: {e}")
         import traceback
         traceback.print_exc()
         return

    # 3. Verify HTML Structure
    checks = [
        ('<table', "Table element found"),
        ('Course / Assignment', "Table Header: Course found"),
        ('Instructor Feedback', "Table Header: Feedback found"),
        ('x-data="{ expanded: false }"', "Alpine.js interactivity found"),
        ('Excellent work!', "Feedback content found"),
        ('95 / 100', "Grade/Performance found")
    ]
    
    all_pass = True
    for needle, desc in checks:
        if needle in content:
            print(f"PASS: {desc}")
        else:
            print(f"FAIL: {desc}")
            all_pass = False
            
    with open('verification_output.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    if all_pass:
        print("\nSUCCESS: UI structure verifies correctly.")
    else:
        print("\nFAILURE: Some UI elements missing. Inspect verification_output.html")


if __name__ == "__main__":
    verify_ui()
