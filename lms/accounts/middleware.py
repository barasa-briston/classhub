from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import logout

class CohortAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.role == 'STUDENT':
            from courses.models import Enrollment
            enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__cohort')
            
            if enrollments.exists():
                all_over = all(e.course.cohort.is_study_period_over for e in enrollments)
                
                # If all cohorts are over, the student should be restricted
                if all_over:
                    # Allow access only to logout or a specific "blocked" page if we had one
                    # For now, let's just allow them to see the dashboard which shows the "Study Period Concluded" message
                    # and prevent them from accessing other things.
                    
                    allowed_paths = [
                        reverse('student-dashboard'),
                        reverse('logout'),
                        reverse('password-reset-request'),
                    ]
                    
                    if not any(request.path == path for path in allowed_paths):
                        messages.warning(request, "Your study period has concluded. Access to this resource is locked.")
                        return redirect('student-dashboard')

        response = self.get_response(request)
        return response
