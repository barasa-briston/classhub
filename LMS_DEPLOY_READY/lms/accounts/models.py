from django.db import models

from django.contrib.auth.models import AbstractUser



# Model for Assignment
class User(AbstractUser):
    # Example field, you can add more if needed
    role = models.CharField(
        max_length=20,
        choices=[('STUDENT', 'Student'), ('LECTURER', 'Lecturer'), ('ADMIN', 'Admin'), ('SUPERADMIN', 'Super Admin')],
        default='STUDENT',
        db_index=True
    )
    # You can add other custom fields like date of birth, address, etc.
    
    def __str__(self):
        return self.username

# Profile for Student users
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='studentprofile')
    cohort = models.ForeignKey('courses.Cohort', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    registration_number = models.CharField(max_length=50, null=True, blank=True, unique=True)

    # Locking & Overrides
    LOCK_CHOICES = [
        ('AUTO', 'Automatic (System Rules)'),
        ('LOCKED', 'Manual: Always Locked'),
        ('UNLOCKED', 'Manual: Always Unlocked'),
    ]
    
    transcript_lock_override = models.CharField(
        max_length=20, 
        choices=LOCK_CHOICES, 
        default='AUTO',
        help_text="Override system rules for Transcript downloads"
    )
    
    def save(self, *args, **kwargs):
        if not self.registration_number:
            import datetime
            year = datetime.date.today().year
            # Get the latest number for this year
            last_profile = StudentProfile.objects.filter(
                registration_number__startswith=f"LMS/{year}/"
            ).order_by('registration_number').last()
            
            if last_profile:
                try:
                    last_num = int(last_profile.registration_number.split('/')[-1])
                    new_num = last_num + 1
                except (IndexError, ValueError):
                    new_num = 1
            else:
                new_num = 1
                
            self.registration_number = f"LMS/{year}/{new_num:04d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile of {self.user.username} ({self.registration_number or 'No Reg'})"

import uuid

class PasswordResetRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_requests')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    new_password_hash = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_resets'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    admin_comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Reset for {self.user.username} ({self.status})"
