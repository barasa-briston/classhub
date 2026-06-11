
import os
import django
import sys
from django.template.loader import render_to_string
from django.conf import settings

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def verify_blinking_refined():
    print("--- Verifying Refined Dashboard Blinking Logic ---")
    
    # Mock context with pending items
    context = {
        'notification_counts': {
            'assignments': 2,
            'grades': 1,
            'payments': 5,
            'resets': 3,
            'total': 11
        },
        'pending_assignments': [],
        'pending_grades': [],
        'assignments': [],
        'submissions': [],
        'students': [],
        'per_page_options': [{'value': 10, 'selected': ''}]
    }
    
    try:
        content = render_to_string('admin_dashboard.html', context)
        
        # Check for pulse-dot class
        if 'pulse-dot' in content:
            print("[PASS] 'pulse-dot' class found in rendered template.")
        else:
            print("[FAIL] 'pulse-dot' class NOT found.")

        # Check for btn-blink class
        if 'btn-blink' in content:
            print("[PASS] 'btn-blink' class found in rendered template.")
        else:
            print("[FAIL] 'btn-blink' class NOT found.")
            
        # Check specifically for the dot inside buttons/headers
        if 'Assignments Needing Approval' in content and 'pulse-dot' in content.split('Assignments Needing Approval')[0][-100:]:
             print("  - Assignments header has pulse dot.")
        
        if 'Manage Resets' in content and 'pulse-dot' in content.split('Manage Resets')[0][-100:]:
             print("  - Manage Resets button has pulse dot.")

    except Exception as e:
        print(f"[ERROR] Rendering failed: {e}")

if __name__ == "__main__":
    verify_blinking_refined()
