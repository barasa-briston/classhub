
import os
import django
import sys
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, FeePayment, Cohort
from accounts.views import (
    student_dashboard, view_fees, download_transcript, download_certificate,
    initiate_mpesa, submit_bank_payment, verify_payments, lecturer_dashboard, admin_dashboard
)

User = get_user_model()

def add_middleware(request):
    SessionMiddleware(lambda x: None).process_request(request)
    MessageMiddleware(lambda x: None).process_request(request)

import random
import string

def get_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def run_verification():
    print("=== STARTING SYSTEM VERIFICATION & PERMISSION CHECK ===\n")
    
    # 1. Setup Data
    print("[1] Setting up Users...")
    hashed_pass = 'password123'
    
    s_user = f"verify_student_{get_random_string()}"
    student, _ = User.objects.get_or_create(username=s_user, email=f'{s_user}@test.com', role='STUDENT')
    if not student.check_password(hashed_pass): student.set_password(hashed_pass); student.save()
        
    l_user = f"verify_lecturer_{get_random_string()}"
    lecturer, _ = User.objects.get_or_create(username=l_user, email=f'{l_user}@test.com', role='LECTURER')
    if not lecturer.check_password(hashed_pass): lecturer.set_password(hashed_pass); lecturer.save()
    
    a_user = f"verify_admin_{get_random_string()}"
    admin, _ = User.objects.get_or_create(username=a_user, email=f'{a_user}@test.com', role='ADMIN')
    if not admin.check_password(hashed_pass): admin.set_password(hashed_pass); admin.save()
    
    print(f"    - Users Ready: Student({s_user}), Lecturer({l_user}), Admin({a_user})")

    factory = RequestFactory()

    # 2. Verify Dashboard Accessibility
    print("\n[2] Verifying Dashboard Access...")
    
    # Student Dashboard
    req = factory.get(reverse('student-dashboard'))
    req.user = student
    resp = student_dashboard(req)
    print(f"    - Student accessing Student Dashboard: {resp.status_code} ({'PASS' if resp.status_code == 200 else 'FAIL'})")
    
    # Lecturer Dashboard
    req = factory.get(reverse('lecturer-dashboard'))
    req.user = lecturer
    resp = lecturer_dashboard(req)
    print(f"    - Lecturer accessing Lecturer Dashboard: {resp.status_code} ({'PASS' if resp.status_code == 200 else 'FAIL'})")
    
    # Admin Dashboard
    req = factory.get(reverse('admin-dashboard'))
    req.user = admin
    resp = admin_dashboard(req)
    print(f"    - Admin accessing Admin Dashboard: {resp.status_code} ({'PASS' if resp.status_code == 200 else 'FAIL'})")

    # 3. Verify Payment Verification Permissions
    print("\n[3] Verifying Payment Verification Access...")
    
    # Lecturer trying to access verify_payments
    req = factory.get(reverse('verify-payments'))
    req.user = lecturer
    try:
        resp = verify_payments(req)
        print(f"    - Lecturer accessing Verify Payments: {resp.status_code} (Should be 404/403)")
    except Http404:
        print("    - Lecturer accessing Verify Payments: PASS (Http404 raised)")
    except Exception as e:
        print(f"    - Lecturer accessing Verify Payments: FAIL (Exception: {e})")

    # Admin accessing verify_payments
    req = factory.get(reverse('verify-payments'))
    req.user = admin
    try:
        resp = verify_payments(req)
        print(f"    - Admin accessing Verify Payments: {resp.status_code} ({'PASS' if resp.status_code == 200 else 'FAIL'})")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"    - Admin accessing Verify Payments: FAIL ({e})")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == '__main__':
    run_verification()
