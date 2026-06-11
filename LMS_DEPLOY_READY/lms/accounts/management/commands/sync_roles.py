from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = "Re-save all users to trigger role->group sync."

    def handle(self, *args, **options):
        count = 0
        for u in User.objects.all():
            u.save()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Synced {count} users."))
