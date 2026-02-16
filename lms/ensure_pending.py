
import os
import django
import sys
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import PasswordResetRequest, User
from courses.models import FeePayment, Course
from assignments.models import Assignment

def ensure_pending_items():
    print("--- Ensuring Pending Items Exist for UI Verification ---")
    
    # 1. Ensure at least one verified password reset
    try:
        user = User.objects.filter(role='STUDENT').first()
        if user:
            req, created = PasswordResetRequest.objects.get_or_create(
                user=user,
                status='PENDING',
                is_verified=True,
                defaults={'new_password_hash': 'forced_hash'}
            )
            if created:
                print(f"Created pending reset for {user.username}")
            else:
                print(f"Pending reset for {user.username} already exists.")
    except Exception as e:
        print(f"Error creating reset: {e}")

    # 2. Ensure at least one pending payment
    try:
        user = User.objects.filter(role='STUDENT').first()
        course = Course.objects.first()
        if user and course:
            payment, created = FeePayment.objects.get_or_create(
                student=user,
                course=course,
                status='PENDING',
                defaults={'amount': Decimal('100.00'), 'transaction_id': 'VERIFY_BLINK'}
            )
            if created:
                print(f"Created pending payment for {user.username}")
            else:
                print(f"Pending payment for {user.username} already exists.")
    except Exception as e:
        print(f"Error creating payment: {e}")

if __name__ == "__main__":
    ensure_pending_items()
