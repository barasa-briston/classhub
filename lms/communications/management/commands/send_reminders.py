from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.contrib.auth import get_user_model
from courses.models import Enrollment, FeePayment
from assignments.models import Assignment, AssignmentAvailability

User = get_user_model()

class Command(BaseCommand):
    help = 'Sends automated email reminders for upcoming deadlines and pending fees.'

    def handle(self, *args, **options):
        self.stdout.write("Starting automated reminders...")
        now = timezone.now()
        tomorrow = now + timedelta(days=1)

        # 1. Assignment Reminders (Due in 24 hours)
        self.stdout.write("Checking for upcoming assignment deadlines...")
        upcoming_availabilities = AssignmentAvailability.objects.filter(
            deadline__gte=now,
            deadline__lte=tomorrow
        ).select_related('assignment', 'cohort')

        for avail in upcoming_availabilities:
            students = User.objects.filter(role='STUDENT', enrollments__cohort=avail.cohort)
            emails = [s.email for s in students if s.email]
            
            if emails:
                subject = f"REMINDER: Assignment '{avail.assignment.title}' Due Soon"
                message = (
                    f"Hello Student,\n\n"
                    f"This is an automated reminder that your assignment '{avail.assignment.title}' "
                    f"for cohort {avail.cohort.name} is due on {avail.deadline.strftime('%Y-%m-%d %H:%M')}.\n\n"
                    f"Please ensure you submit your work on time to avoid penalties.\n\n"
                    f"Best regards,\nCCNA Training Academy"
                )
                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=True)
                    self.stdout.write(self.style.SUCCESS(f"Sent deadline reminders for {avail.assignment.title} to {len(emails)} students."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send deadline reminders: {str(e)}"))

        # 2. Fee Reminders (Students with negative balance or pending payments)
        self.stdout.write("Checking for fee balances...")
        # We look for all active enrollments and check if their total approved payments < course fee
        enrollments = Enrollment.objects.all().select_related('student', 'course', 'cohort')
        
        for enrollment in enrollments:
            total_paid = FeePayment.objects.filter(
                student=enrollment.student,
                course=enrollment.course,
                status='APPROVED'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if total_paid < enrollment.course.fee:
                balance = enrollment.course.fee - Decimal(str(total_paid))
                if enrollment.student.email:
                    subject = f"FEE REMINDER: Balance for {enrollment.course.name}"
                    message = (
                        f"Hello {enrollment.student.username},\n\n"
                        f"Our records show an outstanding balance of KES {balance} for your course: {enrollment.course.name}.\n\n"
                        f"Please ensure your fees are cleared to maintain uninterrupted access to the learning portal and certification downloads.\n\n"
                        f"Best regards,\nAccounts Department, CCNA Academy"
                    )
                    try:
                        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [enrollment.student.email], fail_silently=True)
                        self.stdout.write(f"Sent fee reminder to {enrollment.student.username} (Balance: {balance})")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to send fee reminder to {enrollment.student.username}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Automated reminders task completed."))

# Helper imports for logic inside handle
from django.db.models import Sum
from decimal import Decimal
