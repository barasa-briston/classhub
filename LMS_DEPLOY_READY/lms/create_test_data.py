
import os
import django
from django.utils import timezone
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Course, Cohort, Enrollment, FeePayment
from assignments.models import Assignment
from submissions.models import Submission

User = get_user_model()

def create_test_data():
    print("Creating test data...")

    # 1. Create Student
    student, created = User.objects.get_or_create(username='teststudent', email='test@example.com')
    if created:
        student.set_password('password123')
        student.role = 'STUDENT'
        student.save()
        print(f"Created student: {student.username}")
    else:
        print(f"Student {student.username} already exists")

    # 2. Create Cohort & Course
    cohort, _ = Cohort.objects.get_or_create(name='Test Cohort 2026')
    course, _ = Course.objects.get_or_create(name='Intro to LMS Features', cohort=cohort)
    course.fee = Decimal('5000.00')
    course.save()
    print(f"Created course: {course.name} with fee {course.fee}")

    # 3. Enroll Student
    Enrollment.objects.get_or_create(student=student, course=course)
    print(f"Enrolled {student.username} in {course.name}")

    # 4. Create Fee Payment
    FeePayment.objects.create(
        student=student, 
        course=course, 
        amount=Decimal('2500.00'), 
        transaction_id='TX123ABC', 
        payment_method='M-Pesa'
    )
    print("Created fee payment")

    # 5. Create Assignment & Submission (Marked)
    assignment, _ = Assignment.objects.get_or_create(
        course=course, 
        title='Final Project', 
        defaults={'total_marks': 100, 'deadline': timezone.now() + timezone.timedelta(days=7), 'status': 'APPROVED'}
    )
    
    submission, _ = Submission.objects.get_or_create(
        student=student, 
        assignment=assignment,
        defaults={'is_marked': True, 'marks_awarded': 85.0, 'percentage': 85.0, 'grade': 'P'}
    )
    # Ensure it's marked if it existed but wasn't
    if not submission.is_marked:
        submission.is_marked = True
        submission.marks_awarded = 85.0
        submission.percentage = 85.0
        submission.grade = 'P'
        submission.save()
        
    print(f"Created submission for {assignment.title} with 85 marks")

    print("Test data creation complete.")

if __name__ == '__main__':
    create_test_data()
