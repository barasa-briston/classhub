
import os
import django
from django.test import RequestFactory, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, FeePayment
from accounts.views import initiate_mpesa, submit_bank_payment, verify_payments

User = get_user_model()

def add_middleware(request):
    SessionMiddleware(lambda x: None).process_request(request)
    MessageMiddleware(lambda x: None).process_request(request)

def verify_payments_flow():
    print("Verifying Payment Flows...")
    
    # Setup
    student = User.objects.get(username='teststudent')
    admin_user, _ = User.objects.get_or_create(username='admin_test', email='admin@test.com', role='ADMIN')
    if not admin_user.check_password('adminpass'):
        admin_user.set_password('adminpass')
        admin_user.save()
        
    course = Course.objects.filter(name='Intro to LMS Features').first()
    if not course:
        print("Course not found!")
        return

    factory = RequestFactory()
    
    # 1. Test M-Pesa Initiation
    print("\n1. Testing M-Pesa Initiation...")
    data = {
        'course_id': course.id,
        'amount': '1000',
        'phone_number': '0712345678',
        'transaction_id': 'MPSATEST123'
    }
    request = factory.post(reverse('initiate-mpesa'), data)
    request.user = student
    add_middleware(request)
    
    response = initiate_mpesa(request)
    print(f"M-Pesa Response Code: {response.status_code}") # Should be 302 (redirect)
    
    # Verify DB
    payment = FeePayment.objects.filter(student=student, course=course, payment_method='M-Pesa').last()
    if payment and payment.status == 'PENDING' and payment.amount == 1000:
        print(f"SUCCESS: M-Pesa payment created manually as PENDING. Ref: {payment.transaction_id}")
    else:
        print(f"FAILURE: M-Pesa payment status {payment.status if payment else 'None'} or incorrect.")

    # 2. Test Bank Payment Submission
    print("\n2. Testing Bank Payment Submission...")
    data = {
        'course_id': course.id,
        'amount': '5000',
        'transaction_id': 'BANKREF123'
    }
    request = factory.post(reverse('submit-bank-payment'), data)
    request.user = student
    add_middleware(request)
    
    response = submit_bank_payment(request)
    print(f"Bank Payment Response Code: {response.status_code}") # 302
    
    # Verify DB
    payment = FeePayment.objects.filter(student=student, course=course, payment_method='Bank Transfer', transaction_id='BANKREF123').last()
    if payment and payment.status == 'PENDING':
        print(f"SUCCESS: Bank payment created as PENDING.")
    else:
        print("FAILURE: Bank payment issue.")

    # 3. Test Admin Verification (Approve)
    print("\n3. Testing Admin Verification...")
    if payment:
        data = {'action': 'approve'}
        request = factory.post(reverse('verify-payment', args=[payment.id]), data)
        request.user = admin_user
        add_middleware(request)
        
        response = verify_payments(request, payment_id=payment.id)
        
        payment.refresh_from_db()
        if payment.status == 'APPROVED':
            print("SUCCESS: Payment approved by admin.")
        else:
             print(f"FAILURE: Payment status is {payment.status}")

if __name__ == '__main__':
    verify_payments_flow()
