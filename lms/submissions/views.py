from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from accounts.permissions import IsStudent, IsLecturer, IsAdminOrSuperAdmin
from assignments.models import Assignment
from courses.models import Enrollment
from .models import Submission
from .serializers import SubmissionCreateSerializer, SubmissionListSerializer


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
        if now > assignment.deadline and not assignment.allow_late:
            return Response({"detail": "Deadline passed. Late submission not allowed."}, status=403)

        # Handle retake rule:
        last_submission = Submission.objects.filter(student=request.user, assignment=assignment).order_by("-attempt_number").first()
        attempt_number = 1

        if last_submission:
            if last_submission.is_locked and (last_submission.passed is False):
                # Failed but locked; must be returned/retake-approved (we add that later)
                return Response({"detail": "You cannot resubmit unless a retake is approved."}, status=403)
            attempt_number = last_submission.attempt_number + 1

        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "Upload at least one file using files."}, status=400)

        serializer = SubmissionCreateSerializer(data={"assignment": assignment.id, "files": files})
        serializer.is_valid(raise_exception=True)
        submission = serializer.save(student=request.user, attempt_number=attempt_number)

        # set status to LATE if needed
        if now > assignment.deadline:
            submission.status = Submission.Status.LATE
            submission.save()

        return Response(SubmissionListSerializer(submission).data, status=201)


class StudentMySubmissionsView(generics.ListAPIView):
    serializer_class = SubmissionListSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return Submission.objects.filter(student=self.request.user).order_by("-submitted_at")


class LecturerSubmissionsByAssignmentView(generics.ListAPIView):
    serializer_class = SubmissionListSerializer
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

        submission.score = score
        submission.percentage = round(percentage, 2)
        submission.passed = passed
        submission.graded_by = request.user
        submission.graded_at = timezone.now()
        submission.status = Submission.Status.GRADED
        submission.is_locked = True  # lock after grading
        submission.save()

        return Response(SubmissionListSerializer(submission).data, status=200)


class AdminUnlockSubmissionView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, submission_id):
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({"detail": "Submission not found"}, status=404)

        submission.is_locked = False
        submission.save()
        return Response({"detail": "Submission unlocked. Lecturer can regrade now."}, status=200)
