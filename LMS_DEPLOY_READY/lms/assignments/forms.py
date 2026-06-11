from django import forms
from .models import Assignment, AssignmentAvailability
from courses.models import Cohort

class AssignmentForm(forms.ModelForm):
    cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'})
    )
    
    deadline = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'})
    )
    
    allow_late = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-slate-700 bg-slate-900 text-blue-600 focus:ring-blue-500'})
    )
    
    late_until = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'})
    )
    
    class Meta:
        model = Assignment
        fields = [
            "cohort",
            # course will be auto-derived from cohort
            "module",
            "title",
            "description",
            "total_marks",
            "passmark_percentage",
        ]
        widgets = {
            "title": forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'}),
            "description": forms.Textarea(attrs={'rows': 4, 'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'}),
            "total_marks": forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'}),
            "passmark_percentage": forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'}),
            "module": forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none'}),
        }

    def save(self, commit=True):
        assignment = super().save(commit=False)
        # assignment.course is handled in view or auto-set? 
        # Ideally the view sets assignment.course based on cohort.course or lecturer's course context.
        # But here we just save the Assignment.
        
        if commit:
            assignment.save()
            
            # handle availability
            cohort = self.cleaned_data['cohort']
            deadline = self.cleaned_data['deadline']
            allow_late = self.cleaned_data['allow_late']
            late_until = self.cleaned_data['late_until']
            
            AssignmentAvailability.objects.update_or_create(
                assignment=assignment,
                cohort=cohort,
                defaults={
                    'deadline': deadline,
                    'allow_late': allow_late,
                    'late_until': late_until,
                    'created_by': assignment.created_by # Assuming view sets this on assignment
                }
            )
            
        return assignment
