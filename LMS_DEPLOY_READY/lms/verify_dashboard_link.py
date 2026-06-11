
import os
import django
import sys
from django.urls import reverse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS += ['testserver']

from django.test import Client
from django.contrib.auth import get_user_model

def verify_link():
    print("=== VERIFYING ADMIN DASHBOARD LINK ===")
    User = get_user_model()
    admin_username = 'link_test_admin'
    User.objects.filter(username=admin_username).delete()
    admin = User.objects.create_superuser(admin_username, 'admin@test.com', 'admin')
    
    client = Client()
    client.force_login(admin)
    
    url = reverse('admin-dashboard')
    print(f"GET {url}")
    resp = client.get(url)
    
    if resp.status_code == 200:
        content = resp.content.decode('utf-8')
        target_url = reverse('manage-password-resets')
        
        if target_url in content:
            print(f"[PASS] Link to '{target_url}' found in dashboard.")
        else:
            print(f"[FAIL] Link to '{target_url}' NOT found in dashboard.")
    else:
        print(f"[FAIL] Dashboard returned {resp.status_code}")
        
    User.objects.filter(username=admin_username).delete()

if __name__ == "__main__":
    verify_link()
