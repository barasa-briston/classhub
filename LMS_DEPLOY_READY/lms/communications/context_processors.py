from django.db.models import Count, Q
from .models import Ticket

def unread_messages(request):
    if not request.user.is_authenticated:
        return {'unread_messages_count': 0}
    
    count = 0
    if request.user.role == 'STUDENT':
        count = Ticket.objects.filter(student=request.user).aggregate(
            unread=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
        )['unread'] or 0
    elif request.user.role == 'LECTURER' or request.user.is_superuser:
        from courses.models import Cohort
        if request.user.is_superuser:
            count = Ticket.objects.aggregate(
                unread=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
            )['unread'] or 0
        else:
            cohorts = Cohort.objects.filter(lecturers=request.user)
            count = Ticket.objects.filter(cohort__in=cohorts).aggregate(
                unread=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
            )['unread'] or 0
            
    return {'unread_messages_count': count}
