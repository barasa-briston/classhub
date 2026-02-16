from django import forms
from .models import Assignment

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            "course",
            "title",
            "description",
            "deadline",
            "total_marks",
            "passmark_percentage",
            "allow_late",
        ]
        widgets = {
            "deadline": forms.DateTimeInput(attrs={"type": "datetime-local"})
        }
