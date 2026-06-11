from django.urls import path
from . import web_views

urlpatterns = [
    path("student/", web_views.student_dashboard, name="student-dashboard-legacy"), # Renamed to avoid conclict with main app
    path("student/submit/<int:assignment_id>/", web_views.student_submit, name="student-submit"),
]
