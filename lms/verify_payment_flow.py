
import os
import django
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, FeePayment, Cohort
from accounts.views import initiate_mpesa, verify_payments, admin_dashboard

User = get_user_model()

def add_middleware(request):
    SessionMiddleware(lambda x: None).process_request(request)
    MessageMiddleware(lambda x: None).process_request(request)

def verify_flow():
    print("=== VERIFYING STUDENT PAYMENT & ADMIN APPROVAL FLOW ===\n")
    
    # 0. Setup
    s_user, _ = User.objects.get_or_create(username='flow_student', email='s@test.com', role='STUDENT')
    a_user, _ = User.objects.get_or_create(username='flow_admin', email='a@test.com', role='ADMIN')
    sa_user, _ = User.objects.get_or_create(username='flow_super', email='sa@test.com', role='SUPERADMIN', is_superuser=True)
    
    course, _ = Course.objects.get_or_create(name='Payment Flow Course', fee=5000)
    
    factory = RequestFactory()
    
    # 1. Student Pays via M-Pesa
    print("[1] Student Enters M-Pesa Transaction Code")
    tx_code = 'FLOW_TEST_001'
    data = {
        'course_id': course.id,
        'amount': '1500',
        'phone_number': '0722000000',
        'transaction_id': tx_code
    }
    req = factory.post(reverse('initiate-mpesa'), data)
    req.user = s_user
    add_middleware(req)
    
    initiate_mpesa(req)
    
    payment = FeePayment.objects.filter(transaction_id=tx_code).last()
    if payment:
        print(f"    - Payment Created. Status: {payment.status}")
        if payment.status == 'PENDING':
            print("    - SUCCESS: Payment is waiting for verification.")
        else:
            print("    - FAILURE: Payment should be PENDING.")
    else:
        print("    - FAILURE: Payment not found.")
        return

    # 2. Check Admin Dashboard for Verification Button
    print("\n[2] Admin Checking Dashboard")
    req = factory.get(reverse('admin-dashboard'))
    req.user = a_user
    resp = admin_dashboard(req)
    content = resp.content.decode('utf-8')
    
    if "Verify Payments" in content:
        print("    - SUCCESS: 'Verify Payments' button found on Admin Dashboard.")
    else:
        print("    - FAILURE: 'Verify Payments' button missing.")
        
    if str(payment.status) == 'PENDING':
         # Check if pending count is reflected (simple check)
         pass

    # 3. Super Admin Access
    print("\n[3] Super Admin Checking Dashboard")
    req = factory.get(reverse('admin-dashboard'))
    req.user = sa_user
    resp = admin_dashboard(req)
    if resp.status_code == 200:
        print("    - SUCCESS: Super Admin can access dashboard.")
    else:
        print(f"    - FAILURE: Super Admin blocked ({resp.status_code}).")

    # 4. Admin Verifies Payment
    print("\n[4] Admin Approves Payment")
    data = {'action': 'approve'}
    req = factory.post(reverse('verify-payment', args=[payment.id]), data)
    req.user = a_user
    add_middleware(req)
    
    verify_payments(req, payment_id=payment.id)
    
    payment.refresh_from_db()
    print(f"    - Payment Status after Approval: {payment.status}")
    if payment.status == 'APPROVED':
        print("    - SUCCESS: Payment approved.")
    else:
        print("    - FAILURE: Payment not approved.")

    print("\n=== FLOW VERIFICATION COMPLETE ===")

if __name__ == '__main__':
    verify_flow()
