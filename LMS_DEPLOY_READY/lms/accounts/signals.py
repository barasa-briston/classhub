from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.conf import settings
from django.contrib.auth import get_user_model

# from .models import User, StudentProfile  <-- Removed to fix circular import & missing StudentProfile

LMS_GROUPS = ["Student", "Lecturer", "Admin"]

# Hardcoded roles to match models.py choices if User.Role is missing
ROLE_TO_GROUP = {
    "STUDENT": "Student",
    "LECTURER": "Lecturer",
    "ADMIN": "Admin",
}

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def sync_role_to_group(sender, instance, created, **kwargs):
    # Super admin uses is_superuser=True (skip group sync)
    if instance.is_superuser:
        return

    # Auto-creation of profile is removed here to avoid UNIQUE constraint conflicts 
    # with Admin Inlines and custom views that handle profile creation explicitly.

    group_name = ROLE_TO_GROUP.get(instance.role)
    if not group_name:
        return

    # Ensure group exists
    group, _ = Group.objects.get_or_create(name=group_name)

    # Remove from all LMS groups to avoid conflicts
    instance.groups.remove(*Group.objects.filter(name__in=LMS_GROUPS))

    # Add correct group
    instance.groups.add(group)
