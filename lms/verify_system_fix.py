
import os
import django
import sys
from django.urls import reverse

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS += ['testserver']
settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend' 

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from accounts.models import PasswordResetRequest
from accounts.views import manage_password_resets
from django.core import mail

User = get_user_model()

def verify_system():
    print("=== FULL SYSTEM VERIFICATION: PASSWORD RESET & ADMIN VISIBILITY ===")
    
    # 1. Setup Data
    username = 'verification_user'
    email = 'verify@test.com'
    old_password = 'OldPassword123'
    new_password = 'NewPassword456'
    
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(username=username, email=email, password=old_password, role='STUDENT')
    
    admin_username = 'verify_admin'
    User.objects.filter(username=admin_username).delete()
    admin = User.objects.create_superuser(admin_username, 'admin@test.com', 'admin')
    
    client = Client()
    
    try:
        # --- STEP 1: REQUEST RESET ---
        print("\n[1] User Requesting Reset...")
        resp = client.post(reverse('password-reset-request'), {'username': username})
        
        if resp.status_code != 302:
             print(f"    - [FAIL] Expected 302 Redirect, got {resp.status_code}")
             if hasattr(resp, 'context') and 'form' in resp.context:
                 print("      Form Errors:", resp.context['form'].errors) # If form exists
             # Print content if not redirecting (might be form error page)
             # print(resp.content.decode('utf-8')[:500])
        
        try:
             req = PasswordResetRequest.objects.get(user=user, status='PENDING')
             print(f"    - Request Created: ID {req.id}, Token {req.token}")
        except PasswordResetRequest.DoesNotExist:
             print("    - [FAIL] PasswordResetRequest not created!")
             print("      Response content snippet:", resp.content.decode('utf-8')[:1000])
             return
        
        # --- STEP 2: VERIFY ADMIN VISIBILITY (UNVERIFIED) ---
        print("\n[2] Checking Admin Dashboard for UNVERIFIED request...")
        client.force_login(admin)
        resp = client.get(reverse('manage-password-resets'))
        content = resp.content.decode('utf-8')
        
        if "Pending User Verification" in content and username in content:
            print("    - [PASS] Request is visible under 'Pending User Verification'.")
        else:
            print("    - [FAIL] Request NOT visible in Admin Dashboard (Unverified Stage).")
            print("      Content preview:", content[:500])
            return

        # --- STEP 3: USER SUBMITS NEW PASSWORD ---
        print("\n[3] User Submitting New Password...")
        client.logout() # Ensure user is logged out or anonymous
        # Note: The view doesn't require login, just the token
        
        url = reverse('password-reset-confirm', args=[req.token])
        data = {
            'username': username, # Form triggers validation on this
            'current_password': old_password,
            'new_password': new_password,
            'confirm_password': new_password
        }
        resp = client.post(url, data)
        
        req.refresh_from_db()
        if req.is_verified:
             print("    - [PASS] User verification successful. Request marked as verified.")
        else:
             print("    - [FAIL] User verification failed.")
             if hasattr(resp, 'context') and 'form' in resp.context:
                 print("      Form Errors:", resp.context['form'].errors)
             return

        # --- STEP 4: VERIFY ADMIN VISIBILITY (VERIFIED) ---
        print("\n[4] Checking Admin Dashboard for VERIFIED request...")
        client.force_login(admin)
        resp = client.get(reverse('manage-password-resets'))
        content = resp.content.decode('utf-8')
        
        if "Ready for Approval" in content and username in content:
            print("    - [PASS] Request is visible under 'Ready for Approval'.")
        else:
            print("    - [FAIL] Request NOT visible in 'Ready for Approval'.")
            return

        # --- STEP 5: ADMIN APPROVES ---
        print("\n[5] Admin Approving Request...")
        resp = client.post(reverse('manage-password-resets'), {
            'request_id': req.id,
            'action': 'approve'
        })
        
        req.refresh_from_db()
        if req.status == 'APPROVED':
            print("    - [PASS] Request status is APPROVED.")
        else:
            print(f"    - [FAIL] Request status is {req.status}.")
            return
            
        # --- STEP 6: VERIFY LOGIN WITH NEW PASSWORD ---
        print("\n[6] Verifying Login with New Password...")
        user.refresh_from_db()
        if user.check_password(new_password):
            print("    - [PASS] Password check successful.")
        else:
            print("    - [FAIL] Password check failed.")

    except Exception as e:
        print(f"    - [ERROR] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n[Cleanup] Removing test users...")
        User.objects.filter(username=username).delete()
        User.objects.filter(username=admin_username).delete()

if __name__ == "__main__":
    verify_system()
