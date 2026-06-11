from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from accounts.models import StudentProfile, User
# from courses.models import Cohort, Course, Enrollment
# from assignments.models import Assignment
# from approvals.models import AssignmentApproval


ROLE_PERMS = {
    "Student": [
        # StudentProfile
        ("accounts", "studentprofile", "view_studentprofile"),
        ("accounts", "studentprofile", "change_studentprofile"),

        # Assignments (read-only)
        ("assignments", "assignment", "view_assignment"),

        # Courses / Cohorts (read-only)
        ("courses", "cohort", "view_cohort"),
        ("courses", "course", "view_course"),
        ("courses", "enrollment", "view_enrollment"),
    ],

    "Lecturer": [
        # Student profile view only
        ("accounts", "studentprofile", "view_studentprofile"),

        # Assignments (create + edit + view)
        ("assignments", "assignment", "add_assignment"),
        ("assignments", "assignment", "change_assignment"),
        ("assignments", "assignment", "view_assignment"),

        # Courses/Cohorts view only
        ("courses", "cohort", "view_cohort"),
        ("courses", "course", "view_course"),
        ("courses", "enrollment", "view_enrollment"),

        # Approvals view only (optional)
        ("approvals", "assignmentapproval", "view_assignmentapproval"),
    ],

    "Admin": [
        # Users management (but not delete by default)
        ("accounts", "user", "add_user"),
        ("accounts", "user", "change_user"),
        ("accounts", "user", "view_user"),

        # StudentProfile (Removed as model does not exist)
        # ("accounts", "studentprofile", "view_studentprofile"),
        # ("accounts", "studentprofile", "change_studentprofile"),

        # Courses + Cohorts full
        ("courses", "cohort", "add_cohort"),
        ("courses", "cohort", "change_cohort"),
        ("courses", "cohort", "delete_cohort"),
        ("courses", "cohort", "view_cohort"),

        ("courses", "course", "add_course"),
        ("courses", "course", "change_course"),
        ("courses", "course", "delete_course"),
        ("courses", "course", "view_course"),

        ("courses", "enrollment", "add_enrollment"),
        ("courses", "enrollment", "change_enrollment"),
        ("courses", "enrollment", "delete_enrollment"),
        ("courses", "enrollment", "view_enrollment"),

        # Assignments view (optionally change/delete if you want)
        ("assignments", "assignment", "view_assignment"),

        # Approvals full
        ("approvals", "assignmentapproval", "add_assignmentapproval"),
        ("approvals", "assignmentapproval", "change_assignmentapproval"),
        ("approvals", "assignmentapproval", "delete_assignmentapproval"),
        ("approvals", "assignmentapproval", "view_assignmentapproval"),
    ],
}


class Command(BaseCommand):
    help = "Create default groups (Student, Lecturer, Admin) and assign permissions."

    def handle(self, *args, **options):
        created_groups = []
        for group_name, perms in ROLE_PERMS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_groups.append(group_name)

            # Clear then re-add to keep it consistent
            group.permissions.clear()

            for app_label, model_name, codename in perms:
                try:
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        content_type__model=model_name,
                        codename=codename,
                    )
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Missing permission: {app_label}.{model_name}.{codename}")
                    )

        if created_groups:
            self.stdout.write(self.style.SUCCESS(f"Created groups: {', '.join(created_groups)}"))
        else:
            self.stdout.write(self.style.SUCCESS("Groups already exist. Permissions refreshed."))
