from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def dashboard_redirect(request):
    user = request.user

    if user.is_superuser or user.is_staff:
        return redirect("/admin/")

    role = getattr(user, "role", None)

    if role == "STUDENT":
        return redirect("/student/")
    if role == "LECTURER":
        return redirect("/lecturer/")
    if role == "ADMIN":
        return redirect("/admin/")

    return redirect("/admin/")
