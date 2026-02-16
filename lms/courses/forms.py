from django import forms
from .models import OnlineMeeting, Cohort

class MeetingForm(forms.ModelForm):
    duration_minutes = forms.ChoiceField(
        choices=[
            ('', 'Select Duration'),
            (30, '30 Minutes'),
            (60, '1 Hour'),
            (90, '1.5 Hours'),
            (120, '2 Hours'),
            (180, '3 Hours'),
            (240, '4 Hours'),
        ],
        widget=forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white'})
    )

    class Meta:
        model = OnlineMeeting
        fields = ['cohort', 'topic', 'meeting_date', 'meeting_link', 'meeting_password', 'duration_minutes']
        widgets = {
            'cohort': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white'}),
            'topic': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white', 'placeholder': 'Select course/assignment'}),
            'meeting_date': forms.DateTimeInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white', 'type': 'datetime-local'}),
            'meeting_link': forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white', 'placeholder': 'Input meeting link'}),
            'meeting_password': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white', 'placeholder': 'Input password (Required)'}),
        }

    def __init__(self, *args, **kwargs):
        lecturer = kwargs.pop('lecturer', None)
        super().__init__(*args, **kwargs)
        self.fields['cohort'].empty_label = "Select Cohort"
        if lecturer:
            self.fields['cohort'].queryset = Cohort.objects.filter(lecturers=lecturer)

class RecordingForm(forms.ModelForm):
    class Meta:
        model = OnlineMeeting
        fields = ['recording_url', 'recording_file']
        widgets = {
            'recording_url': forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white', 'placeholder': 'https://... (Recording link)'}),
            'recording_file': forms.ClearableFileInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white'}),
        }
