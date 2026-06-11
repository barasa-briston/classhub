import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assignments.models import Assignment
from django.utils import timezone
from datetime import timedelta

# Get the most recent assignment
recent = Assignment.objects.order_by('-created_at').first()

if recent:
    print(f"\n✅ Most recent assignment:")
    print(f"  ID: {recent.id}")
    print(f"  Title: {recent.title}")
    print(f"  Status: {recent.status}")
    print(f"  Course: {recent.course.name if recent.course else 'NULL'}")
    print(f"  Created by: {recent.created_by.username if recent.created_by else 'NULL'}")
    print(f"  Created at: {recent.created_at}")
    
    # Check if it was created in the last 5 minutes
    time_diff = timezone.now() - recent.created_at
    print(f"  Time since creation: {time_diff}")
    
    if time_diff < timedelta(minutes=5):
        print("\n  ✅ This was created in the last 5 minutes!")
    else:
        print("\n  ❌ This is OLD - your new assignment didn't save!")
else:
    print("❌ No assignments found in database!")

# Check for assignments created in last 10 minutes
recent_assignments = Assignment.objects.filter(
    created_at__gte=timezone.now() - timedelta(minutes=10)
)
print(f"\n✅ Assignments created in last 10 minutes: {recent_assignments.count()}")
for a in recent_assignments:
    print(f"  - {a.title} ({a.status}) at {a.created_at}")
