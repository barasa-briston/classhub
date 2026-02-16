
import os
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from courses.models import FeePayment
# We need to setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.views import admin_dashboard

User = get_user_model()

def verify_student_search():
    print("=== VERIFYING STUDENT SEARCH & PAGINATION ===\n")
    
    # 1. Setup Data
    # Ensure we have enough students for pagination testing
    # We need at least 11 students to test 10 per page
    print("[1] Setting up test data...")
    existing_students = User.objects.filter(role='STUDENT').count()
    needed = 15 - existing_students
    if needed > 0:
        print(f"    - Creating {needed} extra students...")
        for i in range(needed):
            User.objects.create_user(username=f'test_stud_{i}', email=f'test_{i}@school.com', role='STUDENT', password='pass')
    
    # Ensure we have a distinct student for search
    target_student, _ = User.objects.get_or_create(username='search_target', email='target@unique.com', role='STUDENT')
    
    # Ensure we have an admin user
    admin_user, _ = User.objects.get_or_create(username='test_admin', role='ADMIN', is_superuser=True)
    
    factory = RequestFactory()
    
    # 2. Test Pagination (Default 10)
    print("\n[2] Testing Pagination (Default 10 per page)")
    request = factory.get('/admin-dashboard/')
    request.user = admin_user
    
    response = admin_dashboard(request)
    # We can't access context directly from response object returned by render, 
    # unless we use the client. But we can inspect the content or use a trick.
    # Better to use Client to inspect context.
    
    from django.test import Client
    c = Client()
    c.force_login(admin_user)
    
    response = c.get('/admin-dashboard/')
    page_obj = response.context['students']
    print(f"    - Page count: {page_obj.paginator.num_pages}")
    print(f"    - Items on page 1: {len(page_obj)}")
    
    if len(page_obj) == 10:
        print("    - SUCCESS: Default pagination is 10.")
    else:
        print(f"    - FAILURE: Expected 10 items, got {len(page_obj)}")

    # 3. Test Custom Pagination (per_page=50)
    print("\n[3] Testing Custom Pagination (per_page=50)")
    response = c.get('/admin-dashboard/?per_page=50')
    page_obj = response.context['students']
    print(f"    - Items on page 1: {len(page_obj)}")
    
    if len(page_obj) > 10: # We have at least 15 students
        print("    - SUCCESS: Custom pagination works (showing more than 10).")
    else:
        print("    - FAILURE: Pagination did not update.")

    # 4. Test Search
    print("\n[4] Testing Search (q='search_target')")
    response = c.get('/admin-dashboard/?q=search_target')
    page_obj = response.context['students']
    
    found = any(s.username == 'search_target' for s in page_obj)
    count = len(page_obj)
    
    print(f"    - Found 'search_target': {found}")
    print(f"    - Total results: {count}")
    
    if found and count == 1:
        print("    - SUCCESS: Search filtered correctly.")
    elif found and count > 1:
        print("    - WARNING: Search found target but also others (might be loose matching).")
    else:
        print("    - FAILURE: Search did not find target.")

if __name__ == '__main__':
    verify_student_search()
