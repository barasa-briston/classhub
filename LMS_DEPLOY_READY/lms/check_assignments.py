import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assignments.models import Assignment

# Check ALL assignments
all_assignments = Assignment.objects.all()
print(f'\n✅ Total assignments in database: {all_assignments.count()}')

# Check pending assignments
pending = Assignment.objects.filter(status='PENDING')
print(f'✅ Pending assignments: {pending.count()}\n')

if pending.exists():
    print("Pending assignment details:")
    for a in pending:
        print(f"\n  ID: {a.id}")
        print(f"  Title: {a.title}")
        print(f"  Status: {a.status}")
        print(f"  Course: {a.course.name if a.course else 'NULL/MISSING'}")
        print(f"  Created by: {a.created_by.username if a.created_by else 'NULL'}")
        print(f"  Created at: {a.created_at}")
else:
    print("❌ NO PENDING ASSIGNMENTS FOUND!")
    print("\nAll assignment statuses:")
    for status in Assignment.objects.values_list('status', flat=True).distinct():
        count = Assignment.objects.filter(status=status).count()
        print(f"  - {status}: {count}")
