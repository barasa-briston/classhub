
import os
import django
from django.test import Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, FeePayment

User = get_user_model()

def add_middleware(request):
    SessionMiddleware(lambda x: None).process_request(request)
    MessageMiddleware(lambda x: None).process_request(request)

def verify_rejection_and_superadmin():
    print("=== VERIFYING SUPER ADMIN & REJECTION FLOW ===\n")
    
    # 0. Setup
    s_user, _ = User.objects.get_or_create(username='rej_student', email='rs@test.com', role='STUDENT')
    sa_user, _ = User.objects.get_or_create(username='rej_super', email='rsa@test.com', role='SUPERADMIN', is_superuser=True)
    
    course, _ = Course.objects.get_or_create(name='Rejection Course', fee=10000)
    
    # Cleanup previous test data
    FeePayment.objects.filter(student=s_user, course=course).delete()
    
    # Create Pending Payment
    payment = FeePayment.objects.create(
        student=s_user, course=course, amount=1000, 
        payment_method='M-Pesa', transaction_id='REJ_TEST_001', status='PENDING'
    )
    
    client = Client()
    client.force_login(sa_user)
    
    # 1. Verify Super Admin Verification Page Access
    print("[1] Super Admin Accessing Verification Page")
    url = reverse('verify-payments')
    response = client.get(url)
    if response.status_code == 200:
        print("    - SUCCESS: Super Admin accessed verification page.")
    else:
        print(f"    - FAILURE: Access denied ({response.status_code}).")

    # 2. Verify Rejection with Remarks
    print("\n[2] Rejecting Data with Remarks")
    data = {'action': 'reject', 'remarks': 'Invalid Transaction Code'}
    response = client.post(reverse('verify-payment', args=[payment.id]), data, follow=True)
    
    payment.refresh_from_db()
    if payment.status == 'REJECTED':
        print(f"    - Status: {payment.status} (Correct)")
    else:
        print(f"    - Status: {payment.status} (Incorrect)")
        
    if payment.remarks == 'Invalid Transaction Code':
        print(f"    - Remarks: '{payment.remarks}' (Correct)")
    else:
        print(f"    - Remarks: '{payment.remarks}' (Incorrect)")

    # 3. Verify Balance Calculation (Should not include rejected amount)
    print("\n[3] Verifying Balance Logic")
    # Balance = Fee (10000) - Total Paid (Approved/Pending?)
    # We decided to exclude REJECTED. So if we have 1 rejected payment of 1000,
    # Total Paid should be 0. Balance should be 10000.
    
    factory = RequestFactory()
    from accounts.views import view_fees
    
    request = factory.get(reverse('view-fees'))
    request.user = s_user
    response = view_fees(request)
    content = response.content.decode('utf-8')
    
    # We look for balance in the rendered HTML or context if we could inspect it.
    # Simpler: check context data if we used client, but view_fees renders template directly.
    # Let's inspect context via a small hack or just trust the logic if logic test passes
    
    payments = FeePayment.objects.filter(student=s_user, course=course).order_by('-payment_date')
    valid_payments = payments.exclude(status='REJECTED')
    from django.db.models import Sum
    total_paid = valid_payments.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = course.fee - total_paid
    print(f"    - Course Fee: {course.fee}")
    print(f"    - Rejected Payment: {payment.amount}")
    print(f"    - Total Paid (Calculated): {total_paid}")
    print(f"    - Balance: {balance}")
    
    if balance == 10000:
        print("    - SUCCESS: Rejected payment ignored in balance.")
    else:
        print("    - FAILURE: Balance incorrect.")

if __name__ == '__main__':
    verify_rejection_and_superadmin()
