from django import forms
from .models import Notice

class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content', 'cohort', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:border-brand-lightblue transition-colors', 'placeholder': 'e.g., Important Exam Update'}),
            'content': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:border-brand-lightblue transition-colors', 'rows': 4, 'placeholder': 'Type announcement here...'}),
            'cohort': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:border-brand-lightblue transition-colors'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-slate-700 bg-slate-900 text-brand-lightblue focus:ring-brand-lightblue'})
        }
