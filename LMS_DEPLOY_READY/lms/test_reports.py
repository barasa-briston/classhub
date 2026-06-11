from django.test import Client
from django.contrib.auth import get_user_model
import traceback

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

if not admin_user:
    print("No admin user found to test with.")
    exit(1)

client = Client()
client.force_login(admin_user)

try:
    print("--- Testing Fee Balance Report ---")
    response_csv = client.get('/reports/fee-balance/')
    print("CSV Status Code:", response_csv.status_code)

    response_pdf = client.get('/reports/fee-balance/?pdf=1')
    print("PDF Status Code:", response_pdf.status_code)

    print("\n--- Testing Student Progress Report ---")
    response_csv2 = client.get('/reports/student-progress/')
    print("CSV Status Code:", response_csv2.status_code)

    response_pdf2 = client.get('/reports/student-progress/?pdf=1')
    print("PDF Status Code:", response_pdf2.status_code)
except Exception as e:
    traceback.print_exc()

import os
os._exit(0)
