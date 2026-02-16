
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Cohort, Course

User = get_user_model()

print(f"Total Users: {User.objects.count()}")
print(f"Lecturers: {User.objects.filter(role='LECTURER').count()}")
print(f"Students: {User.objects.filter(role='STUDENT').count()}")
print(f"Cohorts: {Cohort.objects.count()}")
print(f"Courses: {Course.objects.count()}")

if User.objects.filter(role='LECTURER').exists():
    print(f"Lecturer: {User.objects.filter(role='LECTURER').first().username}")
if User.objects.filter(role='STUDENT').exists():
    print(f"Student: {User.objects.filter(role='STUDENT').first().username}")
if Cohort.objects.exists():
    print(f"Cohort: {Cohort.objects.first().name}")
if Course.objects.exists():
    print(f"Course: {Course.objects.first().id} - {Course.objects.first().name}")
