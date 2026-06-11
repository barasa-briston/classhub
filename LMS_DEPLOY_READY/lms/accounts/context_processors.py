
from assignments.models import Assignment
from submissions.models import Submission
from courses.models import FeePayment
from .models import PasswordResetRequest

def admin_notifications(request):
    """
    Context processor to provide pending counts for admin dashboard notifications.
    """
    if not request.user.is_authenticated:
        return {}

    # Only query for admins/superusers to save performance on student pages
    if not (request.user.is_superuser or request.user.role in ['ADMIN', 'SUPERADMIN']):
        return {}

    pending_assignments_count = Assignment.objects.filter(status='PENDING').count()
    
    # Grades: Marked but not approved
    pending_grades_count = Submission.objects.filter(is_marked=True, is_approved=False).count()
    
    pending_payments_count = FeePayment.objects.filter(status='PENDING').count()
    
    # Resets: Verified (clicked link) but waiting for admin approval
    pending_resets_count = PasswordResetRequest.objects.filter(status='PENDING', is_verified=True).count()

    return {
        'notification_counts': {
            'assignments': pending_assignments_count,
            'grades': pending_grades_count,
            'payments': pending_payments_count,
            'resets': pending_resets_count,
            'total': pending_assignments_count + pending_grades_count + pending_payments_count + pending_resets_count
        }
    }
