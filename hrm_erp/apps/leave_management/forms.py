from django import forms
from .models import LeaveType, LeaveRequest


class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['name', 'max_days_per_year', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Leave Type Name'}),
            'max_days_per_year': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Description'}),
        }


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-input'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Reason for leave'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date must be on or after start date.')
        return cleaned_data


class LeaveReviewForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['status', 'manager_comment']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-input'}),
            'manager_comment': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Comment'}),
        }
