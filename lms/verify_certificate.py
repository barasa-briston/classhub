import os
import django
import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import get_template
from django.http import HttpResponse
from utils.reports import render_to_pdf
from django.contrib.auth import get_user_model

def verify():
    # Mock data
    student_name = "BRISTON SIMIYU BARASA"
    reg_no = "LMS/2026/0001"
    course_name = "Cisco CCNA 1: Introduction to Networks"
    cert_no = "CU-CS-CCNA1-2026-001"
    issue_date = datetime.date.today()
    start_date = datetime.date(2026, 1, 1)
    end_date = datetime.date(2026, 4, 12)

    context = {
        'student_name': student_name,
        'registration_number': reg_no,
        'course': {'name': course_name},
        'cert_no': cert_no,
        'issue_date': issue_date,
        'start_date': start_date,
        'end_date': end_date,
    }

    print(f"Generating image-based certificate for {student_name}...")
    
    response = render_to_pdf('pdf/certificate.html', context)
    
    if response:
        output_path = os.path.join(os.getcwd(), 'sample_image_cert.pdf')
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Certificate generated successfully: {output_path}")
    else:
        print("Failed to generate certificate PDF.")

if __name__ == "__main__":
    verify()
