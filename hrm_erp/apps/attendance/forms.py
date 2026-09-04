from django import forms
from .models import Attendance


class AttendanceForm(forms.ModelForm):
    """Form for managing attendance records (Admin/HR)."""
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'check_in', 'check_out', 'status', 'late_minutes', 'notes', 'hr_comment']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-input'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'late_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Internal notes'}),
            'hr_comment': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'HR remark visible to the employee...',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        if check_in and check_out and check_out <= check_in:
            raise forms.ValidationError('Check-out time must be after check-in time.')
        return cleaned_data


class HRCommentForm(forms.ModelForm):
    """Minimal form for HR to add/update a comment on an attendance record."""
    class Meta:
        model = Attendance
        fields = ['hr_comment']
        widgets = {
            'hr_comment': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Add HR comment or remark...',
            }),
        }
        labels = {
            'hr_comment': 'HR Comment / Remark',
        }


class AttendancePolicyForm(forms.ModelForm):
    """Form for configuring attendance policy (Admin & HR only)."""
    class Meta:
        from .models import AttendancePolicy
        model = AttendancePolicy
        fields = [
            'title', 'work_start_time', 'work_end_time',
            'grace_period_minutes', 'standard_working_hours',
            'overtime_threshold_hours', 'break_duration',
            'require_location', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'work_start_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'work_end_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'grace_period_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'standard_working_hours': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '0'}),
            'overtime_threshold_hours': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '0'}),
            'break_duration': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '5'}),
            'require_location': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }
