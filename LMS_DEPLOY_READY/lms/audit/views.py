from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import SystemAuditLog
from django.utils import timezone
import datetime

User = get_user_model()

def is_superadmin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superadmin, login_url='/')
def system_audit_logs_view(request):
    logs_list = SystemAuditLog.objects.all().select_related('user').order_by('-timestamp')
    
    # Filtering parameters
    model_filter = request.GET.get('model', '')
    user_filter = request.GET.get('user_id', '')
    action_type = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_q = request.GET.get('q', '')

    if model_filter:
        logs_list = logs_list.filter(model_name=model_filter)
        
    if user_filter:
        logs_list = logs_list.filter(user_id=user_filter)

    if action_type:
        logs_list = logs_list.filter(action=action_type)
    
    if search_q:
        logs_list = logs_list.filter(
            Q(action__icontains=search_q) | 
            Q(object_repr__icontains=search_q) | 
            Q(details__icontains=search_q)
        )

    if date_from:
        try:
            df = timezone.make_aware(datetime.datetime.strptime(date_from, '%Y-%m-%d'))
            logs_list = logs_list.filter(timestamp__gte=df)
        except ValueError:
            pass
            
    if date_to:
        try:
            dt = timezone.make_aware(datetime.datetime.strptime(date_to, '%Y-%m-%d'))
            # Add one day to include the entire 'to' date
            dt = dt + datetime.timedelta(days=1)
            logs_list = logs_list.filter(timestamp__lte=dt)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(logs_list, 50)
    page_number = request.GET.get('page')
    logs = paginator.get_page(page_number)
    
    # Helper data for filters
    distinct_models = SystemAuditLog.objects.values_list('model_name', flat=True).distinct()
    # Get users who have actually performed actions
    user_ids = SystemAuditLog.objects.values_list('user_id', flat=True).distinct()
    active_users = User.objects.filter(id__in=user_ids)
    
    action_types = ['CREATED', 'UPDATED', 'DELETED', 'APPROVED', 'REJECTED', 'LOGIN', 'LOGOUT']
    
    context = {
        'logs': logs,
        'distinct_models': distinct_models,
        'active_users': active_users,
        'action_types': action_types,
        'model_filter': model_filter,
        'user_filter': user_filter,
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        'search_q': search_q,
    }
    
    return render(request, 'audit/audit_logs.html', context)
