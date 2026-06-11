from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def student_home(request):
    return HttpResponse("Student Dashboard OK ✅")


@login_required
def lecturer_home(request):
    return HttpResponse("Lecturer Dashboard OK ✅")
