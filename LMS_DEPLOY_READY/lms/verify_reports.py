
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from accounts.views import generate_enrollment_report, generate_payment_report
from django.contrib.auth import get_user_model

User = get_user_model()

def verify_reports():
    print("=== VERIFYING REPORT GENERATION ===")
    
    # Setup Admin User
    admin, _ = User.objects.get_or_create(username='report_admin', email='ra@test.com', role='ADMIN')
    factory = RequestFactory()
    
    # 1. Enrollment Report (CSV)
    request = factory.get('/reports/enrollment/')
    request.user = admin
    response = generate_enrollment_report(request)
    if response.status_code == 200 and response['Content-Type'] == 'text/csv':
        print("SUCCESS: Enrollment CSV generated.")
    else:
        print(f"FAILURE: Enrollment CSV failed {response.status_code}")

    # 2. Enrollment Report (PDF)
    request = factory.get('/reports/enrollment/?pdf=1')
    request.user = admin
    response = generate_enrollment_report(request)
    if response.status_code == 200 and response['Content-Type'] == 'application/pdf':
        print("SUCCESS: Enrollment PDF generated.")
    else:
        print(f"FAILURE: Enrollment PDF failed {response.status_code}")
        
    # 3. Payment Report (CSV)
    request = factory.get('/reports/payment/')
    request.user = admin
    response = generate_payment_report(request)
    if response.status_code == 200 and response['Content-Type'] == 'text/csv':
        print("SUCCESS: Payment CSV generated.")
    else:
        print(f"FAILURE: Payment CSV failed {response.status_code}")

    # 4. Payment Report (PDF)
    request = factory.get('/reports/payment/?pdf=1')
    request.user = admin
    response = generate_payment_report(request)
    if response.status_code == 200 and response['Content-Type'] == 'application/pdf':
        print("SUCCESS: Payment PDF generated.")
    else:
        print(f"FAILURE: Payment PDF failed {response.status_code}")

if __name__ == '__main__':
    verify_reports()
