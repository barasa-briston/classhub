
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Enrollment, Cohort

User = get_user_model()
student = User.objects.get(username="barasa")
cohort = Cohort.objects.get(name="CCNA 1")

enrollment, created = Enrollment.objects.get_or_create(student=student, course=cohort.course_set.first() if cohort.course_set.exists() else None)
enrollment.cohort = cohort
enrollment.save()

print(f"Fixed: Student {student.username} is now in Cohort {cohort.name}")
