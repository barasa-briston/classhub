import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms')) # Add inner lms folder just in case
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Course, Cohort, FeePayment
from django.test import RequestFactory
from accounts.views import initiate_mpesa, submit_bank_payment
from django.contrib.messages.storage.fallback import FallbackStorage

User = get_user_model()

def verify_provider_logic():
    print("--- Verifying Provider Logic ---")
    
    # 1. Setup Data
    student, _ = User.objects.get_or_create(username='test_student_provider', role='STUDENT')
    course, _ = Course.objects.get_or_create(name='Provider Test Course', fee=5000)
    
    # 2. Test Mobile Payment (M-Pesa)
    factory = RequestFactory()
    request = factory.post('/accounts/initiate-mpesa/', {
        'course_id': course.id,
        'amount': 1000,
        'phone_number': '0712345678',
        'transaction_id': 'MPESA_TEST_01',
        'provider': 'M-Pesa' 
    })
    request.user = student
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    initiate_mpesa(request)
    
    # Verify M-Pesa Record
    mpesa_payment = FeePayment.objects.filter(transaction_id='MPESA_TEST_01').first()
    if mpesa_payment and mpesa_payment.provider == 'M-Pesa' and mpesa_payment.payment_method == 'Mobile Money':
        print(f"PASS: M-Pesa Payment saved correctly. Provider: {mpesa_payment.provider}")
    else:
        print(f"FAIL: M-Pesa Payment logic failed. Payment: {mpesa_payment}")

    # 3. Test Mobile Payment (Airtel) - clean up first if needed, or use new ID
    request = factory.post('/accounts/initiate-mpesa/', {
        'course_id': course.id,
        'amount': 1000,
        'phone_number': '0733333333',
        'transaction_id': 'AIRTEL_TEST_01',
        'provider': 'Airtel Money'
    })
    request.user = student
    setattr(request, 'session', 'session')
    setattr(request, '_messages', messages)
    
    initiate_mpesa(request)
    
    airtel_payment = FeePayment.objects.filter(transaction_id='AIRTEL_TEST_01').first()
    if airtel_payment and airtel_payment.provider == 'Airtel Money' and airtel_payment.payment_method == 'Mobile Money':
        print(f"PASS: Airtel Payment saved correctly. Provider: {airtel_payment.provider}")
    else:
        print(f"FAIL: Airtel Payment logic failed. Payment: {airtel_payment}")

    # 4. Test Bank Payment (KCB)
    request = factory.post('/accounts/submit-bank-payment/', {
        'course_id': course.id,
        'amount': 2000,
        'transaction_id': 'BANK_TEST_01',
        'bank_name': 'KCB Bank Kenya'
    })
    request.user = student
    setattr(request, 'session', 'session')
    setattr(request, '_messages', messages)
    
    submit_bank_payment(request)
    
    bank_payment = FeePayment.objects.filter(transaction_id='BANK_TEST_01').first()
    if bank_payment and bank_payment.provider == 'KCB Bank Kenya' and bank_payment.payment_method == 'Bank Transfer':
        print(f"PASS: Bank Payment (KCB) saved correctly. Provider: {bank_payment.provider}")
    else:
        print(f"FAIL: Bank Payment logic failed. Payment: {bank_payment}")

    # Clean up
    # FeePayment.objects.filter(student=student).delete()
    # course.delete()
    # student.delete()

if __name__ == "__main__":
    verify_provider_logic()
