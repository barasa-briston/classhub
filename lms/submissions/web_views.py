from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect

def is_student(user):
    return getattr(user, "role", "") == "STUDENT"

@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    """
    Redirect legacy dashboard URL to the new enhanced student dashboard.
    """
    return redirect("student-dashboard") # Points to accounts:student-dashboard

@login_required
@user_passes_test(is_student)
def student_submit(request, assignment_id):
    """
    Redirect legacy submission URL to the new file upload interface.
    """
    return redirect("submit-assignment", assignment_id=assignment_id)
