
import os
import django
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.views import student_dashboard, view_fees, download_transcript, download_certificate
from courses.models import Course, Enrollment

User = get_user_model()

def verify_views():
    print("Verifying views...")
    
    # Get Test User
    user = User.objects.get(username='teststudent')
    print(f"Testing with user: {user.username}")
    
    factory = RequestFactory()
    
    # 1. Test Student Dashboard
    print("1. Testing Student Dashboard...")
    request = factory.get(reverse('student-dashboard'))
    request.user = user
    response = student_dashboard(request)
    print(f"Dashboard Response Code: {response.status_code}")
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        if "My Fees" in content:
            print("SUCCESS: 'My Fees' button found.")
        else:
            print("FAILURE: 'My Fees' button NOT found.")
            
        if "Download Transcript" in content:
            print("SUCCESS: 'Download Transcript' button found.")
        else:
            print("FAILURE: 'Download Transcript' button NOT found.")
    else:
        print("FAILURE: Dashboard did not load.")

    # 2. Test View Fees
    print("\n2. Testing View Fees...")
    request = factory.get(reverse('view-fees'))
    request.user = user
    response = view_fees(request)
    print(f"Fees Page Response Code: {response.status_code}")
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        if "My Fees" in content and "Intro to LMS Features" in content:
            print("SUCCESS: Fees page loaded with correct content.")
        else:
            print("FAILURE: Fees page content mismatch.")

    # 3. Test Download Transcript
    print("\n3. Testing Download Transcript...")
    # Get the course we created
    course = Course.objects.get(name='Intro to LMS Features')
    request = factory.get(reverse('download-transcript', args=[course.id]))
    request.user = user
    response = download_transcript(request, course.id)
    print(f"Transcript Response Code: {response.status_code}")
    print(f"Content-Type: {response.get('Content-Type')}")
    if response.status_code == 200 and response.get('Content-Type') == 'application/pdf':
         print("SUCCESS: Transcript PDF generated.")
    else:
         print("FAILURE: Transcript PDF generation failed.")

    # 4. Test Download Certificate
    print("\n4. Testing Download Certificate...")
    request = factory.get(reverse('download-certificate', args=[course.id]))
    request.user = user
    # Mocking cohort over or passed
    response = download_certificate(request, course.id)
    print(f"Certificate Response Code: {response.status_code}")
    # It might redirect if conditions aren't met, or return PDF
    if response.status_code == 200 and response.get('Content-Type') == 'application/pdf':
         print("SUCCESS: Certificate PDF generated.")
    elif response.status_code == 302:
         print("NOTICE: Certificate redirected (likely due to conditions). Checking logic...")
    else:
         print(f"FAILURE: Certificate generation failed with code {response.status_code}.")

if __name__ == '__main__':
    verify_views()
