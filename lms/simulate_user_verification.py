
import os
import django
import sys
from django.contrib.auth.hashers import make_password

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import PasswordResetRequest, User

def simulate_verification():
    username = 'mercy'
    print(f"--- Simulating User Verification for '{username}' ---")
    
    try:
        user = User.objects.get(username=username)
        req = PasswordResetRequest.objects.filter(user=user, status='PENDING').latest('requested_at')
        
        print(f"Found pending request ID: {req.id}")
        
        # Simulate user entering new password 'newpassword123'
        req.new_password_hash = make_password('newpassword123')
        req.is_verified = True
        req.save()
        
        print(f"Successfully updated request {req.id}.")
        print(f"  Verified: {req.is_verified}")
        print(f"  Has Hash: YES")
        print("This request should now appear in the 'Ready for Approval' section.")
        
    except User.DoesNotExist:
        print(f"User '{username}' not found.")
    except PasswordResetRequest.DoesNotExist:
        print(f"No pending request found for '{username}'.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    simulate_verification()
