from django.urls import path
from .views import dashboard_redirect
from .simple_pages import student_home, lecturer_home

urlpatterns = [
    path("dashboard/", dashboard_redirect, name="dashboard"),
    path("student/", student_home, name="student-home"),
    path("lecturer/", lecturer_home, name="lecturer-home"),
]
