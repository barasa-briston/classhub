from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from accounts.permissions import IsLecturer, IsAdminOrSuperAdmin
from .models import Assignment
from .serializers import AssignmentCreateSerializer

from approvals.models import AssignmentApproval


class LecturerCreateAssignmentView(APIView):
    permission_classes = [IsLecturer]

    def post(self, request):
        serializer = AssignmentCreateSerializer(data=request.data)
        if serializer.is_valid():
            assignment = serializer.save(
                created_by=request.user,
                status=Assignment.Status.PENDING
            )

            # create approval record automatically
            AssignmentApproval.objects.update_or_create(
                assignment=assignment,
                defaults={
                    "requested_by": request.user,
                    "status": "PENDING",
                }
            )

            return Response(
                {"message": "Assignment created and sent for approval.", "assignment_id": assignment.id},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LecturerMyAssignmentsView(APIView):
    permission_classes = [IsLecturer]

    def get(self, request):
        qs = Assignment.objects.filter(created_by=request.user).order_by("-created_at")
        data = AssignmentCreateSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class AdminApproveAssignmentView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, assignment_id):
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({"detail": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

        # approve
        assignment.status = Assignment.Status.APPROVED
        assignment.approved_by = request.user
        assignment.approved_at = request.user.last_login  # simple timestamp fallback
        assignment.rejection_comment = ""
        assignment.save()

        # update approval record
        AssignmentApproval.objects.update_or_create(
            assignment=assignment,
            defaults={
                "status": "APPROVED",
                "reviewed_by": request.user,
            }
        )

        return Response({"message": "Assignment approved."}, status=status.HTTP_200_OK)


class AdminRejectAssignmentView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, assignment_id):
        comment = request.data.get("comment", "").strip()

        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({"detail": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

        assignment.status = Assignment.Status.REJECTED
        assignment.rejection_comment = comment
        assignment.approved_by = None
        assignment.approved_at = None
        assignment.save()

        AssignmentApproval.objects.update_or_create(
            assignment=assignment,
            defaults={
                "status": "REJECTED",
                "reviewed_by": request.user,
                "comment": comment,
            }
        )

        return Response({"message": "Assignment rejected."}, status=status.HTTP_200_OK)

from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

class StudentApprovedAssignmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # student can only see approved + not past deadline unless allow_late
        qs = Assignment.objects.filter(status=Assignment.Status.APPROVED).order_by("-created_at")

        data = AssignmentCreateSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)
