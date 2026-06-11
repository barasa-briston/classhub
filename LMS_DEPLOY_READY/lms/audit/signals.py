from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import threading

# Thread-local storage to pass the current user from middleware to signals
_thread_locals = threading.local()

def set_current_user(user):
    _thread_locals.user = user

def get_current_user():
    return getattr(_thread_locals, 'user', None)

from .models import SystemAuditLog

# Only audit these critical models for now
AUDIT_MODELS = ['FeePayment', 'Submission', 'Assignment', 'User', 'Cohort']

def create_audit_log(sender, instance, action, **kwargs):
    model_name = sender.__name__
    if model_name not in AUDIT_MODELS:
        return
        
    user = get_current_user()
    
    # Try fetching object details gracefully
    try:
        object_repr = str(instance)
    except Exception:
        object_repr = f"{model_name} object ({instance.pk})"
        
    # Serialize basic primitive types for details
    import json
    details = ""
    try:
        if action != "DELETED":
            from django.core.serializers.json import DjangoJSONEncoder
            data = {}
            for field in instance._meta.fields:
                val = getattr(instance, field.name)
                # To prevent exposing passwords in logs
                if field.name == 'password':
                    val = "******"
                data[field.name] = val
            details = json.dumps(data, cls=DjangoJSONEncoder)
    except Exception:
        details = "Could not serialize details"

    SystemAuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(instance.pk),
        object_repr=object_repr,
        details=details
    )

@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    action = "CREATED" if created else "UPDATED"
    # Special catch for Submissions/Payments if they transition to APPROVED/LOCKED
    if sender.__name__ == 'FeePayment' and not created:
        if getattr(instance, 'status', None) in ['APPROVED', 'REJECTED']:
            action = f"UPDATED (Marked {instance.status})"
            
    create_audit_log(sender, instance, action, **kwargs)

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    create_audit_log(sender, instance, "DELETED", **kwargs)
