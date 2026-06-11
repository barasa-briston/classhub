from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

def is_student(u): return getattr(u, "role", "") == "STUDENT"
def is_lecturer(u): return getattr(u, "role", "") == "LECTURER"
def is_admin(u): return u.is_superuser or getattr(u, "role", "") == "ADMIN"

@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    return render(request, "dashboard/student.html")

@login_required
@user_passes_test(is_lecturer)
def lecturer_dashboard(request):
    return render(request, "dashboard/lecturer.html")

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    return render(request, "dashboard/admin.html")
