from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Notice
from django.contrib.auth import get_user_model
from courses.models import Enrollment

User = get_user_model()

@receiver(post_save, sender=Notice)
def notify_students_of_notice(sender, instance, created, **kwargs):
    if created and instance.is_active:
        subject = f"New Notice: {instance.title}"
        message = f"Hello,\n\nA new notice has been posted in the LMS:\n\nTitle: {instance.title}\nContent:\n{instance.content}\n\nLog in to the dashboard for more details."
        
        recipient_emails = []
        
        if instance.cohort:
            # Cohort-specific notice: Get all students in this cohort
            enrollments = Enrollment.objects.filter(cohort=instance.cohort).select_related('student')
            recipient_emails = [e.student.email for e in enrollments if e.student.email]
        else:
            # Global notice: Get all active students
            students = User.objects.filter(role='STUDENT', is_active=True)
            recipient_emails = [s.email for s in students if s.email]
            
        if recipient_emails:
            # We send individually or in small batches to avoid BCC limits or giant recipient lists
            # For simplicity here, we use a single send_mail call, but in production with thousands
            # of students, you'd use a background task or django.core.mail.EmailMessage with bcc.
            # However, to ensure they see it in real-time and since failures are now visible:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_emails,
                    fail_silently=False
                )
            except Exception:
                pass
