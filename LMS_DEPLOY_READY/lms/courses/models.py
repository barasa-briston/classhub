from django.db import models
from django.conf import settings


class Cohort(models.Model):
    name = models.CharField(max_length=100)  # e.g. CCNA 1, CCNA 2
    intake_label = models.CharField(max_length=100, blank=True)  # e.g. Feb 2026 Intake
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    lecturers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_cohorts',
        blank=True
    )

    class Meta:
        unique_together = ("name", "intake_label")

    def __str__(self):
        label = f" {self.intake_label}" if self.intake_label else ""
        return f"{self.name}{label}"

    @property
    def is_study_period_over(self):
        """Returns True if today is past the cohort's end_date"""
        from django.utils import timezone
        if not self.end_date:
            return False
        return timezone.now().date() > self.end_date


class Course(models.Model):
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="courses",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        if self.cohort:
            return f"{self.name} ({self.cohort.name})"
        return self.name

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        
    def __str__(self):
        return f"{self.course.name} - {self.name}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    # Locking & Overrides
    LOCK_CHOICES = [
        ('AUTO', 'Automatic (System Rules)'),
        ('LOCKED', 'Manual: Always Locked'),
        ('UNLOCKED', 'Manual: Always Unlocked'),
    ]
    
    certificate_lock_override = models.CharField(
        max_length=20, 
        choices=LOCK_CHOICES, 
        default='AUTO',
        help_text="Override system rules for Certificate downloads"
    )

    manual_certificate = models.FileField(
        upload_to='certificates/manual/', 
        blank=True, 
        null=True, 
        help_text="Upload a custom certificate (PDF/JPG/PNG) to bypass automated generation"
    )

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student.username} -> {self.course}"


class FeePayment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, blank=True) # e.g. Mobile Money, Bank Transfer
    provider = models.CharField(max_length=50, blank=True) # e.g. M-Pesa, KCB, Equity
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPROVED')
    phone_number = models.CharField(max_length=15, blank=True)
    remarks = models.TextField(blank=True, help_text="Reason for rejection or admin notes")
    bank_slip = models.FileField(upload_to='bank_slips/', max_length=255, blank=True, null=True, help_text="Upload bank slip (JPG or PDF)")

    def __str__(self):
        return f"{self.student} paid {self.amount} for {self.course} [{self.status}]"

class OnlineMeeting(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='meetings')
    topic = models.CharField(max_length=255)
    meeting_date = models.DateTimeField(db_index=True)
    meeting_link = models.URLField(max_length=500)
    meeting_password = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Duration of class in minutes")
    
    # Recording info
    recording_url = models.URLField(max_length=500, blank=True, null=True)
    recording_file = models.FileField(upload_to='recordings/', max_length=255, blank=True, null=True)
    recording_shared_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.topic} - {self.cohort.name}"
    
    @property
    def is_recording_available(self):
        if not self.recording_shared_at:
            return False
        from django.utils import timezone
        import datetime
        # Available 24 hours after the class
        return timezone.now() > self.meeting_date + datetime.timedelta(hours=24)

    @property
    def is_active(self):
        """Returns True if the meeting is currently in progress based on duration."""
        from django.utils import timezone
        import datetime
        now = timezone.now()
        end_time = self.meeting_date + datetime.timedelta(minutes=self.duration_minutes)
        return self.meeting_date <= now <= end_time

    def is_punctual(self, join_time, threshold_minutes=30):
        """Checks if the join_time is within the first X minutes of the class."""
        import datetime
        limit = self.meeting_date + datetime.timedelta(minutes=threshold_minutes)
        return join_time <= limit

class AttendanceRecord(models.Model):
    # ... (existing fields)
    meeting = models.ForeignKey(OnlineMeeting, on_delete=models.CASCADE, related_name='attendance_logs')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_attended = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ('meeting', 'student')
        indexes = [
            models.Index(fields=['meeting', 'student', 'is_attended']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.meeting.topic}"


class Resource(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True, null=True, help_text="Optional link to external documentation/site")
    icon_class = models.CharField(max_length=50, default="fa-file-pdf", help_text="FontAwesome icon class (e.g., fa-file-pdf, fa-link)")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Course)
def auto_duplicate_modules_for_new_course(sender, instance, created, **kwargs):
    """
    When a NEW Course is created (e.g. for a new Cohort), automatically copy modules 
    from the most recent existing Course with the same name.
    This ensures that 'CCNA 1' for 'Feb Cohort' gets the same modules as 'CCNA 1' for 'Jan Cohort'.
    """
    if created and not instance.modules.exists():
        # Find a source course: Same name, different ID, has modules, most recent first
        source_course = Course.objects.filter(name=instance.name) \
                                      .exclude(pk=instance.pk) \
                                      .annotate(module_count=models.Count('modules')) \
                                      .filter(module_count__gt=0) \
                                      .order_by('-id') \
                                      .first()
        
        if source_course:
            # Copy modules
            modules_to_copy = source_course.modules.all()
            new_modules = [
                Module(course=instance, name=m.name, order=m.order)
                for m in modules_to_copy
            ]
            Module.objects.bulk_create(new_modules)
            print(f"Auto-duplicated {len(new_modules)} modules from {source_course.id} to new course {instance.id}")

