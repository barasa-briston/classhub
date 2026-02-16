import os
import django
from django.template import Template, Context
from django.conf import settings
import datetime

import sys
# Create a robust path to the project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import render_to_string

def verify_template(template_name, context):
    try:
        rendered = render_to_string(template_name, context)
        if '{{' in rendered or '}}' in rendered:
            print(f"FAIL: {template_name} contains unrendered tags.")
            # Print the lines with tags for debugging
            for i, line in enumerate(rendered.split('\n')):
                if '{{' in line or '}}' in line:
                    print(f"  Line {i+1}: {line.strip()}")
            return False
        else:
            print(f"PASS: {template_name} renders cleanly.")
            return True
    except Exception as e:
        print(f"ERROR: {template_name} failed to render. {e}")
        import traceback
        traceback.print_exc()
        return False

# Mock Class
class Mock:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def __str__(self):
        return "MockObject"

# Complex Mocks
mock_user = Mock(username="testuser", role="STUDENT", is_superuser=False)
mock_lecturer = Mock(username="lecturer", role="LECTURER")

mock_cohort = Mock(name="Cohort 1", intake_label="Jan 2024", start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2024, 6, 1), is_study_period_over=False)
mock_course = Mock(name="Python 101", cohort=mock_cohort, id=1)
mock_enrollment = Mock(course=mock_course)

mock_assignment = Mock(title="Assignment 1", description="Desc", total_marks=100, deadline=datetime.datetime(2024, 12, 31), id=1, course=mock_course, status="APPROVED", created_by=mock_lecturer)
mock_submission = Mock(student=mock_user, assignment=mock_assignment, submitted_at=datetime.datetime(2024, 2, 1), marks_awarded=80, percentage=80.0, is_marked=True, grade="A", feedback="Good job", is_locked=False)

# Contexts
mock_context_student = {
    'all_over': False,
    'avg_mark': 75.5,
    'pass_status': 'PASS',
    'submissions': [mock_submission],
    'enrollments': [mock_enrollment],
    'available_assignments': [mock_assignment],
    'user': mock_user
}

mock_context_admin = {
    'pending_payments_count': 5,
    'assignments': [mock_assignment],
    'submissions': [mock_submission],
    'pending_assignments': [mock_assignment],
    'pending_grades': [mock_submission],
    'user': Mock(username="admin", is_superuser=True)
}

mock_context_lecturer = {
    'cohorts': [mock_cohort],
    'assignments': [mock_assignment],
    'pending_submissions': [mock_submission],
    'marked_submissions': [mock_submission],
    'user': mock_lecturer
}

print("Verifying Templates...")
success = True
print("Checking Student Dashboard...")
success &= verify_template('student_dashboard.html', mock_context_student)
print("Checking Admin Dashboard...")
success &= verify_template('admin_dashboard.html', mock_context_admin)
print("Checking Lecturer Dashboard...")
success &= verify_template('lecturer_dashboard.html', mock_context_lecturer)

if not success:
    exit(1)
print("All Dashboard Templates Verified Successfully!")
