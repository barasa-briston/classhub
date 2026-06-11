import os
import django
from django.urls import reverse
import sys

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    url = reverse('reject-assignment', args=[1])
    print(f"Success! URL is: {url}")
except Exception as e:
    print(f"Error reversing URL: {e}")
