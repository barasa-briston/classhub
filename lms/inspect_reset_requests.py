
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import PasswordResetRequest

def inspect_requests():
    print("--- Inspecting Pending Password Reset Requests ---")
    requests = PasswordResetRequest.objects.filter(status='PENDING')
    
    if not requests.exists():
        print("No pending requests found.")
        return

    print(f"{'User':<15} | {'Verified':<8} | {'Has Hash':<8} | {'ID'}")
    print("-" * 50)
    for req in requests.order_by('-requested_at')[:10]:
        hashed = 'YES' if req.new_password_hash else 'NO'
        print(f"{req.user.username:<15} | {str(req.is_verified):<8} | {hashed:<8} | {req.id}")

if __name__ == "__main__":
    inspect_requests()
