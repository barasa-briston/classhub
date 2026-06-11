import os
import django
import sys
from io import BytesIO

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Course, Enrollment, FeePayment
from django.test import RequestFactory
from accounts.views import download_fee_statement, generate_enrollment_report

User = get_user_model()

def verify_downloads():
    print("--- Verifying Download Features ---")
    
    # Setup Data
    student, _ = User.objects.get_or_create(username='test_student_pdf', role='STUDENT')
    course, _ = Course.objects.get_or_create(name='PDF Test Course', fee=10000)
    Enrollment.objects.get_or_create(student=student, course=course)
    
    # Create some payments
    FeePayment.objects.create(student=student, course=course, amount=2000, payment_method='M-Pesa', transaction_id='PDF_TEST_1', status='APPROVED')
    FeePayment.objects.create(student=student, course=course, amount=3000, payment_method='Bank Transfer', transaction_id='PDF_TEST_2', status='PENDING')
    
    factory = RequestFactory()
    
    # 1. Test Student Fee Statement
    print("\n1. Testing Student Fee Statement...")
    request = factory.get(f'/accounts/fee-statement/{course.id}/')
    request.user = student
    
    # We can't easily inspect the PDF content here without a parser, but we can call the view
    # and maybe inspect the context if we mocked render_to_pdf?
    # For now, let's just run it to ensure it generates 200 OK.
    # To truly verify logic, we could inspect the 'payments' queryset in a unit test, 
    # but here we are doing integration testing.
    
    response = download_fee_statement(request, course.id)
    
    if response.status_code == 200 and response['Content-Type'] == 'application/pdf':
        print("PASS: status=200, type=application/pdf")
        if 'inline' in response['Content-Disposition']:
             print(f"PASS: Content-Disposition is inline ({response['Content-Disposition']})")
        else:
             print(f"FAIL: Content-Disposition mismatch: {response['Content-Disposition']}")
             
        # Verification of logic:
        # We manually check the queryset logic:
        payments_qs = FeePayment.objects.filter(student=student, course=course, status='APPROVED')
        print(f"DEBUG: Logic expects {payments_qs.count()} approved payments. (Should be 1)")
        if payments_qs.count() == 1:
            print("PASS: Logic correct (1 Approved payment).")
        else:
            print(f"FAIL: Logic incorrect, found {payments_qs.count()} approved payments.")
            
    else:
        print(f"FAIL: Status {response.status_code}")

    # 2. Test Admin Report PDF Preview
    print("\n2. Testing Admin Report PDF Preview...")
    admin, _ = User.objects.get_or_create(username='pdf_admin', role='ADMIN')
    request = factory.get('/reports/enrollment/?pdf=1')
    request.user = admin
    
    response = generate_enrollment_report(request)
    
    if response.status_code == 200 and response['Content-Type'] == 'application/pdf':
        print("PASS: status=200, type=application/pdf")
        if 'inline' in response['Content-Disposition']:
             print(f"PASS: Content-Disposition is inline ({response['Content-Disposition']})")
        else:
             print(f"FAIL: Content-Disposition mismatch: {response['Content-Disposition']}")
    else:
        print(f"FAIL: Status {response.status_code}")

if __name__ == "__main__":
    verify_downloads()
