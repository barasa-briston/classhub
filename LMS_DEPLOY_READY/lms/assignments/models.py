import re
from django.db import models
from django.conf import settings
from courses.models import Course


class Assignment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        ARCHIVED = "ARCHIVED", "Archived"

    # One course field only (you had it twice)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Removed deadline and allow_late fields - moved to AssignmentAvailability

    total_marks = models.PositiveIntegerField(default=100)
    passmark_percentage = models.FloatField(default=50.0)

    module = models.ForeignKey(
        'courses.Module',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    is_exam = models.BooleanField(
        default=False,
        help_text="Check if this assignment should be treated as an Exam (higher priority display)."
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments_created",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments_approved",
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sort_key = models.CharField(max_length=50, blank=True, null=True, editable=False)

    def save(self, *args, **kwargs):
        match = re.search(r'(?:[Mm]odules?\s*)?(\d+(?:\.\d+)*)', self.title or "")
        if match:
            section = match.group(1)
            parts = section.split('.')
            self.sort_key = '.'.join(p.zfill(4) for p in parts)
        else:
            self.sort_key = (self.title or "").lower()[:50]
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"

class AssignmentAvailability(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="availabilities"
    )
    cohort = models.ForeignKey(
        'courses.Cohort',
        on_delete=models.CASCADE,
        related_name="assignment_availabilities"
    )
    deadline = models.DateTimeField()
    allow_late = models.BooleanField(default=False)
    late_until = models.DateTimeField(null=True, blank=True)
    late_penalty = models.FloatField(default=0.0, help_text="Percentage penalty for late submission (e.g. 10.0 for 10% reduction).")
    reopen_until = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('assignment', 'cohort')
        verbose_name_plural = "Assignment Availabilities"

    def __str__(self):
        return f"{self.assignment.title} for {self.cohort.name}"
