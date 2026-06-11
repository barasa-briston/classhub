
import os
import django
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, FeePayment
from accounts.views import initiate_mpesa

User = get_user_model()

def add_middleware(request):
    SessionMiddleware(lambda x: None).process_request(request)
    MessageMiddleware(lambda x: None).process_request(request)

def debug_mpesa_error():
    print("=== DEBUGGING M-PESA PAYMENT ERROR ===\n")
    
    # Setup
    student = User.objects.filter(role='STUDENT').first()
    if not student:
        student = User.objects.create_user('debug_student', 'debug@test.com', 'pass', role='STUDENT')
        
    course = Course.objects.first()
    if not course:
        print("No course found!")
        return

    factory = RequestFactory()
    
    # 1. Test Missing Fields
    print("[1] Testing Missing Transaction ID (Common Error)")
    data = {
        'course_id': course.id,
        'amount': '1000',
        'phone_number': '0712345678'
        # 'transaction_id': MISSING
    }
    request = factory.post(reverse('initiate-mpesa'), data)
    request.user = student
    add_middleware(request)
    
    try:
        response = initiate_mpesa(request)
        print(f"    - Response Code: {response.status_code}")
    except Exception as e:
        print(f"    - EXCEPTION CAUGHT: {e}")

    # 2. Test Invalid Course ID
    print("\n[2] Testing Invalid Course ID")
    data = {
        'course_id': 99999,
        'amount': '1000',
        'transaction_id': 'TEST_INV_COURSE',
        'phone_number': '0712345678'
    }
    request = factory.post(reverse('initiate-mpesa'), data)
    request.user = student
    add_middleware(request)
    
    try:
        response = initiate_mpesa(request)
        print(f"    - Response Code: {response.status_code}")
    except Exception as e:
         print(f"    - EXCEPTION CAUGHT (Expected 404): {e}")

    # 3. Test Empty Amount
    print("\n[3] Testing Empty Amount")
    data = {
        'course_id': course.id,
        'amount': '',
        'transaction_id': 'TEST_EMPTY_AMT',
        'phone_number': '0712345678'
    }
    request = factory.post(reverse('initiate-mpesa'), data)
    request.user = student
    add_middleware(request)
    
    try:
        response = initiate_mpesa(request)
        print(f"    - Response Code: {response.status_code}")
    except Exception as e:
         print(f"    - EXCEPTION CAUGHT: {e}")

if __name__ == '__main__':
    debug_mpesa_error()
