from django.urls import path
from . import views

urlpatterns = [
    path('student/inbox/', views.student_inbox, name='student-inbox'),
    path('lecturer/inbox/', views.lecturer_inbox, name='lecturer-inbox'),
    path('thread/<int:ticket_id>/', views.ticket_thread, name='ticket-thread'),
    path('post-discussion/<int:assignment_id>/', views.post_discussion, name='post-discussion'),
    path('discussion/<int:assignment_id>/', views.assignment_discussion, name='assignment-discussion'),
    path('notice/new/', views.create_notice, name='create-notice'),
    path('bulk-congratulate/', views.bulk_congratulate, name='bulk-congratulate'),
]
