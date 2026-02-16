
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS += ['testserver']
settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

from django.contrib.auth import get_user_model
from accounts.models import PasswordResetRequest
from django.test import Client
from django.urls import reverse

User = get_user_model()

def test_user_flow(role, username, email):
    print(f"\n--- Testing Flow for Role: {role} ---")
    client = Client()
    
    old_password = 'OldPassword123'
    new_password = 'NewPassword456'
    
    # Clean and Create User
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(username=username, email=email, password=old_password, role=role)
    print(f"    - User '{username}' created with role '{role}'")
    
    # Clear Outbox
    from django.core import mail
    mail.outbox = []
    
    # 2. Request Reset
    print("    [1] Requesting Reset...")
    url = reverse('password-reset-request')
    response = client.post(url, {'username': username})
    
    if response.status_code != 302:
         print(f"    - [FAIL] Request failed with status {response.status_code}")
         return False

    try:
        reset_req = PasswordResetRequest.objects.get(user=user, status='PENDING')
        print(f"    - [PASS] Request created. Token found.")
    except PasswordResetRequest.DoesNotExist:
        print("    - [FAIL] PasswordResetRequest not found!")
        return False

    # Check Emails
    if len(mail.outbox) >= 2:
        print(f"    - [PASS] Emails sent: {len(mail.outbox)} (Expected at least 2: User + Admin)")
        
        # Verify User Email
        user_email = next((m for m in mail.outbox if user.email in m.to), None)
        if user_email and "Password Reset Request" in user_email.subject:
             print("    - [PASS] User received reset link email.")
        else:
             print("    - [FAIL] User email missing or incorrect subject.")

        # Verify Admin Email
        admin_email = next((m for m in mail.outbox if "New Password Reset Request" in m.subject), None)
        if admin_email:
             print("    - [PASS] Admins received notification email.")
        else:
             print("    - [FAIL] Admin notification email missing.")
    else:
        print(f"    - [FAIL] Incorrect email count. Sent: {len(mail.outbox)}")

    # 3. Confirm (User side)
    print("    [2] User Confirming...")
    url = reverse('password-reset-confirm', args=[reset_req.token])
    data_valid = {
        'current_password': old_password,
        'new_password': new_password,
        'confirm_password': new_password
    }
    response = client.post(url, data_valid)
    
    reset_req.refresh_from_db()
    if reset_req.is_verified and reset_req.new_password_hash:
        print("    - [PASS] User verified and hash stored.")
    else:
        print("    - [FAIL] User verification failed.")
        return False

    # 4. Admin Approval
    print("    [3] Admin Approving...")
    admin_user = User.objects.get(username='reset_admin') # Assumed created in main
    client.force_login(admin_user)
    manage_url = reverse('manage-password-resets')
    response = client.post(manage_url, {
        'request_id': reset_req.id,
        'action': 'approve'
    })
    
    reset_req.refresh_from_db()
    if reset_req.status == 'APPROVED':
        print("    - [PASS] Admin Approved.")
    else:
        print(f"    - [FAIL] Admin approval failed. Status: {reset_req.status}")
        return False
        
    # 5. Verify Login with New Password
    user.refresh_from_db()
    if user.check_password(new_password):
        print("    - [PASS] Password successfully changed.")
        return True
    else:
        print("    - [FAIL] Password update failed.")
        return False

def verify_all_roles():
    print("=== VERIFYING PASSWORD RESET FLOW FOR ALL ROLES ===\n")
    
    # Setup Admin
    User.objects.filter(username='reset_admin').delete()
    User.objects.create_superuser('reset_admin', 'admin@test.com', 'admin')
    
    roles_to_test = [
        ('STUDENT', 'test_student', 'student@test.com'),
        ('LECTURER', 'test_lecturer', 'lecturer@test.com'),
        ('ADMIN', 'test_admin_user', 'admin_user@test.com') 
    ]
    
    all_passed = True
    for role, username, email in roles_to_test:
        if not test_user_flow(role, username, email):
            all_passed = False
            
    print("\n=== FINAL RESULT ===")
    if all_passed:
        print("SUCCESS: Password reset verified for ALL roles (Student, Lecturer, Admin).")
    else:
        print("FAILURE: Some roles failed verification.")

import traceback

if __name__ == "__main__":
    try:
        # Redirect stdout to file
        with open('verification_results.txt', 'w') as f:
            sys.stdout = f
            verify_all_roles()
    except Exception as e:
        with open('verification_results.txt', 'a') as f:
            f.write(f"CRASH: {e}\n")
            traceback.print_exc(file=f)
