import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assignments.models import Assignment

# Check pending assignments
pending = Assignment.objects.filter(status='PENDING')
print(f'\n✅ Total pending assignments: {pending.count()}')
print('\nPending assignments details:')
for a in pending[:5]:
    course_name = a.course.name if a.course else "No course"
    creator = a.created_by.username if a.created_by else "Unknown"
    print(f'  - Title: {a.title}')
    print(f'    Created by: {creator}')
    print(f'    Course: {course_name}')
    print(f'    Status: {a.status}')
    print()

print('✅ Admin dashboard should now display these assignments!')
