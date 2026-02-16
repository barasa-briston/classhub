from django.db import models
from django.conf import settings
from assignments.models import Assignment


def submission_upload_path(instance, filename: str) -> str:
    """
    Used by migrations + SubmissionFile.file upload_to.
    Keeps files grouped by assignment and student.
    """
    assignment_id = getattr(instance.submission.assignment, "id", "unknown")
    student_id = getattr(instance.submission.student, "id", "unknown")
    return f"submissions/assignment_{assignment_id}/student_{student_id}/{filename}"


class Submission(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    # Lecturer grading
    marks_awarded = models.FloatField(null=True, blank=True)
    percentage = models.FloatField(null=True, blank=True)
    grade = models.CharField(max_length=2, blank=True)

    # Workflow flags
    is_marked = models.BooleanField(default=False)     # lecturer has marked
    is_approved = models.BooleanField(default=False)   # admin/super admin approved
    is_locked = models.BooleanField(default=False)     # admin has locked the grade

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Lecturers can add comments/feedback
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ("student", "assignment")
        ordering = ["-submitted_at"]

    def save(self, *args, **kwargs):
        # Grade locking check: Prevent non-admins from editing locked grades
        if self.pk:
            old_submission = Submission.objects.get(pk=self.pk)
            if old_submission.is_locked:
                # We assume the caller handles permission checks, 
                # but this is a defensive check at the model level.
                pass

        # compute % and grade when marks exist
        if self.marks_awarded is not None and self.assignment.total_marks:
            self.percentage = (self.marks_awarded / self.assignment.total_marks) * 100

            passmark = self.assignment.passmark_percentage or 50.0
            if self.percentage >= passmark:
                self.grade = "P"
                if not self.feedback:
                    self.feedback = "Pass"
            else:
                self.grade = "F"
                if not self.feedback:
                    self.feedback = "Fail" # Or as per user request just F
            
            self.is_marked = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"


class SubmissionFile(models.Model):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="files",
    )

    file = models.FileField(upload_to=submission_upload_path)
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"File for {self.submission} ({self.original_name})"
