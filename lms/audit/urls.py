from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.system_audit_logs_view, name='system-audit-logs'),
]
