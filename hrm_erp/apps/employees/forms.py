import os
from django import forms
from .models import Employee


ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB


class EmployeeForm(forms.ModelForm):
    """Form for HR/Admin to create/edit employees. Email is read-only when editing."""

    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'date_of_birth', 'gender', 'address', 'photo',
            'hire_date', 'department', 'designation', 'branch',
            'status', 'basic_salary',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone number'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Address'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/jpeg,image/png,image/webp'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-input'}),
            'designation': forms.Select(attrs={'class': 'form-input'}),
            'branch': forms.Select(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0.00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email address is read-only after account creation
        if self.instance and self.instance.pk:
            self.fields['email'].widget.attrs['readonly'] = 'readonly'
            self.fields['email'].widget.attrs['class'] = 'form-input form-input-readonly'
            self.fields['email'].help_text = 'Email address is locked and cannot be changed after creation.'

    def clean_email(self):
        """Enforce read-only email address on edit."""
        if self.instance and self.instance.pk:
            return self.instance.email
        return self.cleaned_data.get('email')

    def clean_photo(self):
        """Validate uploaded photo: type and size."""
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'content_type'):
            if photo.content_type not in ALLOWED_IMAGE_TYPES:
                raise forms.ValidationError('Only JPEG, PNG, and WebP images are allowed.')
            if photo.size > MAX_IMAGE_SIZE:
                raise forms.ValidationError('Image size must be under 2MB.')
        return photo


class EmployeeSelfUpdateForm(forms.ModelForm):
    """Form for employees to update basic personal profile details only."""

    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'phone',
            'date_of_birth', 'gender', 'address', 'photo',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last name'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone number'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Address'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/jpeg,image/png,image/webp'}),
        }

    def clean_photo(self):
        """Validate uploaded photo: type and size."""
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'content_type'):
            if photo.content_type not in ALLOWED_IMAGE_TYPES:
                raise forms.ValidationError('Only JPEG, PNG, and WebP images are allowed.')
            if photo.size > MAX_IMAGE_SIZE:
                raise forms.ValidationError('Image size must be under 2MB.')
        return photo
