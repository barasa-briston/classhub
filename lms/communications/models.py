from django.db import models
from django.conf import settings
from courses.models import Cohort
from assignments.models import Assignment

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_tickets')
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='tickets')
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.cohort.name}] {self.subject} - {self.student.username}"

    class Meta:
        ordering = ['-updated_at']

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.sender.username} on {self.ticket.subject}"

    class Meta:
        ordering = ['created_at']

class Notice(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    # If cohort is None, it's a global notice. If specified, it's cohort-specific.
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='notices', null=True, blank=True)
    # Individual recipient (optional)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_notices', null=True, blank=True)
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_notices')
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this notice from students.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        prefix = ""
        if self.recipient:
            prefix = f"[TO: {self.recipient.username}] "
        elif self.cohort:
            prefix = f"[{self.cohort.name}] "
        else:
            prefix = "[GLOBAL] "
        return f"{prefix}{self.title}"

    class Meta:
        ordering = ['-created_at']

class DiscussionMessage(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='discussions')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignment_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Discussion by {self.sender.username} on {self.assignment.title}"

    class Meta:
        ordering = ['created_at']
