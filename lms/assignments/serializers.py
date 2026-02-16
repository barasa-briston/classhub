from rest_framework import serializers
from .models import Assignment


class AssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "id",
            "course",
            "title",
            "description",
            "deadline",
            "total_marks",
            "passmark_percentage",
            "allow_late",
        ]

    def validate_passmark_percentage(self, value):
        if value is None:
            return 75.0  # default pass mark
        if value < 0 or value > 100:
            raise serializers.ValidationError("Passmark must be between 0 and 100.")
        return value
