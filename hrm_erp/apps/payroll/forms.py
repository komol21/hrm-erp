from django import forms
from .models import Payroll


class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['employee', 'month', 'basic_salary', 'allowances', 'deductions', 'payment_status', 'payment_date', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-input'}),
            'month': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'YYYY-MM (e.g. 2026-08)'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'form-input'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Notes'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # HR managers cannot generate their own payment slips.
        # Filter out HR user's own employee record from selection list for HR users (unless Admin).
        if self.user and self.user.is_hr() and not self.user.is_admin():
            hr_employee = self.user.get_employee()
            if hr_employee:
                self.fields['employee'].queryset = self.fields['employee'].queryset.exclude(pk=hr_employee.pk)

    def clean_employee(self):
        employee = self.cleaned_data.get('employee')
        if self.user and self.user.is_hr() and not self.user.is_admin():
            hr_employee = self.user.get_employee()
            if hr_employee and employee == hr_employee:
                raise forms.ValidationError('HR managers cannot generate their own payment slip. Please contact an Admin.')
        return employee

    def clean_month(self):
        month = self.cleaned_data.get('month')
        if month:
            # Check format YYYY-MM
            import re
            if not re.match(r'^\d{4}-\d{2}$', month):
                raise forms.ValidationError('Month must be in YYYY-MM format.')
        return month
