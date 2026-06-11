
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course

print("--- Verifying Course Names ---")
print("ID | String Representation")
print("-" * 40)
for course in Course.objects.all().select_related('cohort'):
    print(f"{course.id} | {course}")
