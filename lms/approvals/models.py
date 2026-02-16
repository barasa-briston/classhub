from django.db import models
from django.conf import settings
from assignments.models import Assignment


class AssignmentApproval(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    assignment = models.OneToOneField(
        Assignment,
        on_delete=models.CASCADE,
        related_name="approval"
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignment_approvals_requested"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_approvals_reviewed"
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.assignment.title} - {self.status}"
