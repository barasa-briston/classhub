
@login_required
@require_POST
def reset_submission(request, submission_id):
    if not request.user.role in ['LECTURER', 'ADMIN', 'SUPERADMIN']:
        messages.error(request, "Unauthorized action.")
        return redirect('lecturer-dashboard')
        
    submission = get_object_or_404(Submission, id=submission_id)
    
    # 1. Unlock
    submission.is_locked = False
    submission.is_marked = False # Also unmark it so it's not "graded" anymore
    submission.score = None
    submission.percentage = None
    submission.passed = None
    submission.graded_by = None
    submission.graded_at = None
    submission.save()
    
    messages.success(request, f"Submission for {submission.student.username} has been reset and unlocked.")
    return redirect('lecturer-dashboard')
