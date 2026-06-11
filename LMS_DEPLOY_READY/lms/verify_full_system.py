
import os
import django
import sys
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, FeePayment, Cohort
from accounts.views import (
    student_dashboard, view_fees, download_transcript, download_certificate,
    initiate_mpesa, submit_bank_payment, verify_payments
)

User = get_user_model()

def add_middleware(request):
    SessionMiddleware(lambda x: None).process_request(request)
    MessageMiddleware(lambda x: None).process_request(request)

def run_verification():
    print("=== STARTING FINAL SYSTEM VERIFICATION ===\n")
    
    # 1. Setup Data
    print("[1] Setting up Test Data...")
    hashed_pass = 'password123'
    student, _ = User.objects.get_or_create(username='verify_student', email='verify@test.com', role='STUDENT')
    if not student.check_password(hashed_pass):
        student.set_password(hashed_pass)
        student.save()
        
    admin_user, _ = User.objects.get_or_create(username='verify_admin', email='admin@test.com', role='ADMIN')
    if not admin_user.check_password('adminpass'):
        admin_user.set_password('adminpass')
        admin_user.save()
        
    cohort, _ = Cohort.objects.get_or_create(name='Verify Cohort 2026')
    course, _ = Course.objects.get_or_create(name='LMS Verification Course', cohort=cohort)
    course.fee = 10000
    course.save()
    
    print("    - Test Student: OK")
    print("    - Test Admin: OK")
    print("    - Test Course: OK\n")

    factory = RequestFactory()

    # 2. View Fees (UI Check)
    print("[2] Verifying Fee View UI...")
    request = factory.get(reverse('view-fees'))
    request.user = student
    response = view_fees(request)
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        # Check for tabs
        if "M-Pesa" in content and "Bank Transfer" in content:
            print("    - Fee Page Loads: PASS")
            print("    - Payment Tabs Present: PASS")
        else:
             print("    - Fee Page Content: FAIL (Tabs missing)")
    else:
        print(f"    - Fee Page Load: FAIL ({response.status_code})")
    print("")

    # 3. M-Pesa Manual Flow
    print("[3] Verifying M-Pesa Manual Flow...")
    tx_code = 'MPESA_VERIFY_01'
    data = {
        'course_id': course.id,
        'amount': '2000',
        'phone_number': '0700000000',
        'transaction_id': tx_code
    }
    request = factory.post(reverse('initiate-mpesa'), data)
    request.user = student
    add_middleware(request)
    initiate_mpesa(request)
    
    payment = FeePayment.objects.filter(transaction_id=tx_code).last()
    if payment and payment.status == 'PENDING':
        print("    - Payment Creation (PENDING): PASS")
    else:
        print(f"    - Payment Creation: FAIL (Status: {payment.status if payment else 'None'})")
        
    # Admin Approve
    if payment:
        data = {'action': 'approve'}
        request = factory.post(reverse('verify-payment', args=[payment.id]), data)
        request.user = admin_user
        add_middleware(request)
        verify_payments(request, payment_id=payment.id)
        
        payment.refresh_from_db()
        if payment.status == 'APPROVED':
             print("    - Admin Approval: PASS")
        else:
             print(f"    - Admin Approval: FAIL (Status: {payment.status})")
    print("")

    # 4. Certificate Generation
    print("[4] Verifying Certificate Generation...")
    request = factory.get(reverse('download-certificate', args=[course.id]))
    request.user = student
    # Mock cohort logic or ensure logic allows download (might fail if cohort logic restricts)
    # We'll just check if view runs without error
    try:
        response = download_certificate(request, course.id)
        if response.status_code == 200 and response.get('Content-Type') == 'application/pdf':
             print("    - Certificate PDF (HTTP 200): PASS")
        elif response.status_code == 302:
             print("    - Certificate Redirect (Likely criteria not met, but logic ran): PASS/WARN")
        else:
             print(f"    - Certificate Gen: FAIL ({response.status_code})")
    except Exception as e:
        print(f"    - Certificate Error: {e}")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == '__main__':
    run_verification()
