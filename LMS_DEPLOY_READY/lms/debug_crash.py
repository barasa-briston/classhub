
import os
import django
import sys
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

def debug_run():
    try:
        User = get_user_model()
        username = 'crash_test_user'
        User.objects.filter(username=username).delete()
        user = User.objects.create_user(username=username, email='crash@test.com', password='password')
        print("User created.")
        
        client = Client()
        url = reverse('password-reset-request')
        print(f"Posting to {url}")
        
        resp = client.post(url, {'username': username})
        print(f"Response status: {resp.status_code}")
        
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    with open('crash_report.txt', 'w') as f:
        sys.stderr = f
        sys.stdout = f
        debug_run()
