from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from accounts.permissions import IsStudent, IsLecturer, IsAdminOrSuperAdmin
from assignments.models import Assignment, AssignmentAvailability
from courses.models import Enrollment
from .models import Submission, SubmissionFile
from .serializers import SubmissionSerializer
from communications.models import Notice


class StudentSubmitAssignmentView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        """
        multipart/form-data:
        assignment=<id>
        files=<multiple files>
        """
        assignment_id = request.data.get("assignment")
        if not assignment_id:
            return Response({"detail": "assignment is required"}, status=400)

        try:
            assignment = Assignment.objects.get(id=assignment_id, status=Assignment.Status.APPROVED)
        except Assignment.DoesNotExist:
            return Response({"detail": "Assignment not found or not approved."}, status=404)

        # Student must be enrolled in the assignment course
        is_enrolled = Enrollment.objects.filter(student=request.user, course=assignment.course).exists()
        if not is_enrolled:
            return Response({"detail": "You are not enrolled in this course."}, status=403)

        # Deadline rule
        now = timezone.now()
        
        availability = AssignmentAvailability.objects.filter(
            assignment=assignment, 
            cohort__courses__enrollments__student=request.user
        ).first()
        
        effective_deadline = availability.deadline if availability else None
        allow_late = availability.allow_late if availability else False
        
        if effective_deadline and now > effective_deadline and not allow_late:
            return Response({"detail": "Deadline passed. Late submission not allowed."}, status=403)

        # Handle retake/resubmission rule:
        # Check if a submission already exists for this student and assignment
        submission = Submission.objects.filter(student=request.user, assignment=assignment).first()

        if submission:
            if submission.is_locked:
                # If locked (and implicitly marked/graded), student cannot resubmit unless admin unlocks it.
                return Response({"detail": "Submission is locked/graded. Contact admin to unlock for resubmission."}, status=403)
            
            # If not locked, we UPDATE the existing submission.
            # Reset fields to treat it as a new attempt
            submission.last_submitted_at = now
            submission.marks_awarded = None
            submission.percentage = None
            submission.grade = ""
            submission.is_marked = False
            submission.is_approved = False  # Reset admin approval/locking
            submission.feedback = ""
            
            # Handle status (check deadline again)
            if effective_deadline and now > effective_deadline:
                 # Logic for late submission status if you had a status field (removed in migration, but kept in mind)
                 pass
            
            submission.save()
            
            # --- CUSTOM LOGIC: Delete old files for fresh resubmission ---
            submission.files.all().delete() # Bulk delete related files
            # -------------------------------------------------------------
            
            # Handle file uploads - we can either append or replace. 
            # Usually for a true 'fresh' resubmission, we might want to keep history or just replace.
            # detailed requirement: "unlock results for student to resubmit".
            # Simplest approach: The new files are added to the existing submission. 
            # If you want to CLEAR old files, do: submission.files.all().delete()
            # For now, let's keep old files just in case, or maybe specific file replacement is needed.
            # Let's just append new files for now.
        else:
            pass

        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "Upload at least one file using files."}, status=400)

        if not submission:
            # CREATE
            submission = Submission.objects.create(
                student=request.user,
                assignment=assignment,
                # submitted_at=now (auto_now_add handles creation time, but we might want to update it on save for updates)
            )
        
        # Save files
        from .models import SubmissionFile
        for f in files:
            SubmissionFile.objects.create(submission=submission, file=f)

        return Response(SubmissionSerializer(submission).data, status=201)


class StudentMySubmissionsView(generics.ListAPIView):
    serializer_class = SubmissionSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return Submission.objects.filter(student=self.request.user).order_by("-submitted_at")


class LecturerSubmissionsByAssignmentView(generics.ListAPIView):
    serializer_class = SubmissionSerializer
    permission_classes = [IsLecturer]

    def get_queryset(self):
        assignment_id = self.kwargs["assignment_id"]
        return Submission.objects.filter(assignment_id=assignment_id).order_by("-submitted_at")


class LecturerGradeSubmissionView(APIView):
    permission_classes = [IsLecturer]

    def post(self, request, submission_id):
        """
        body json:
        {
          "score": 78
        }
        """
        try:
            submission = Submission.objects.select_related("assignment").get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({"detail": "Submission not found"}, status=404)

        if submission.is_locked:
            return Response({"detail": "Submission is locked. Admin must unlock to regrade."}, status=403)

        score = request.data.get("score")
        if score is None:
            return Response({"detail": "score is required"}, status=400)

        try:
            score = float(score)
        except ValueError:
            return Response({"detail": "score must be a number"}, status=400)

        if score < 0 or score > submission.assignment.total_marks:
            return Response({"detail": f"score must be between 0 and {submission.assignment.total_marks}"}, status=400)

        total = float(submission.assignment.total_marks)
        percentage = (score / total) * 100

        # passmark: assignment override else default 75
        passmark = submission.assignment.passmark_percentage if submission.assignment.passmark_percentage is not None else 75.0
        passed = percentage >= float(passmark)

        submission.marks_awarded = score
        # submission.save() will handle percentage, grade, and is_marked
        
        # --- CUSTOM LOGIC: Auto-unlock for resubmission if failed ---
        # Note: save() logic in models.py handles pass/fail based on percentage
        # We need to compute it here to decide on locking
        if not passed:
            submission.is_locked = False
            # Send Notification to Student
            Notice.objects.create(
                title=f"Action Required: Redo {submission.assignment.title}",
                content=(
                    f"Hi {submission.student.username}, you did not reach the pass mark for "
                    f"'{submission.assignment.title}'. The system has automatically allowed "
                    f"you to redo and resubmit your work. Please review the feedback and try again."
                ),
                recipient=submission.student,
                author=request.user
            )
        else:
            submission.is_locked = True  # lock after grading if passed
        # -----------------------------------------------------------

        submission.save()

        return Response(SubmissionSerializer(submission).data, status=200)


class AdminUnlockSubmissionView(APIView):
    permission_classes = [IsAdminOrSuperAdmin | IsLecturer]

    def post(self, request, submission_id):
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({"detail": "Submission not found"}, status=404)

        submission.is_locked = False
        submission.is_marked = False
        submission.marks_awarded = None
        submission.save()
        return Response({"detail": "Submission unlocked. Lecturer can regrade now."}, status=200)
