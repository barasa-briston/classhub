from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def due_date_color(deadline):
    if not deadline:
        return "gray"
    
    now = timezone.now()
    if deadline < now:
        return "red"
    elif deadline < now + timedelta(days=2):
        return "orange"
    else:
        return "green"
