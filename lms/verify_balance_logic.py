
import os
import django
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, FeePayment, Cohort
from django.contrib.auth import get_user_model

User = get_user_model()

def verify_balance():
    print("=== VERIFYING BALANCE LOGIC ONLY ===")
    
    # Setup
    student, _ = User.objects.get_or_create(username='bal_test', email='bt@test.com', role='STUDENT')
    course, _ = Course.objects.get_or_create(name='Balance Test Course', fee=10000)
    
    # Cleanup
    FeePayment.objects.filter(student=student, course=course).delete()
    
    # Create REJECTED payment
    p1 = FeePayment.objects.create(
        student=student, course=course, amount=1000, 
        transaction_id='REJ_001', status='REJECTED'
    )
    
    # Create APPROVED payment
    p2 = FeePayment.objects.create(
        student=student, course=course, amount=2000, 
        transaction_id='APP_001', status='APPROVED'
    )
    
    print(f"Created P1 (Rejected): {p1.amount}, Status: '{p1.status}'")
    print(f"Created P2 (Approved): {p2.amount}, Status: '{p2.status}'")
    
    # Test Query
    payments = FeePayment.objects.filter(student=student, course=course)
    valid_payments = payments.exclude(status='REJECTED')
    
    print(f"All Payments Count: {payments.count()}")
    print(f"Valid Payments Count: {valid_payments.count()}")
    for p in valid_payments:
        print(f" - Valid Payment: {p.amount} ({p.status})")
        
    total_paid = valid_payments.aggregate(Sum('amount'))['amount__sum'] or 0
    print(f"Total Paid: {total_paid}")
    
    expected_paid = 2000
    if total_paid == expected_paid:
        print("SUCCESS: Logic works correctly.")
    else:
        print(f"FAILURE: Expected {expected_paid}, got {total_paid}")

if __name__ == '__main__':
    verify_balance()
