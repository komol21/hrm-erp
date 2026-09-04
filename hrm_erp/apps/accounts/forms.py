import re
from django import forms
from django.core.validators import validate_email
from .models import User, Role


EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'


def validate_email_format(email):
    """Validate email address format supporting domains like @gmail.com, @yahoo.com, etc."""
    if not email:
        raise forms.ValidationError('Email address is required.')
    email_clean = email.strip().lower()
    if not re.match(EMAIL_REGEX, email_clean):
        raise forms.ValidationError('Enter a valid email address (e.g. user@gmail.com, user@yahoo.com).')
    try:
        validate_email(email_clean)
    except forms.ValidationError:
        raise forms.ValidationError('Enter a valid email address.')
    return email_clean


class LoginForm(forms.Form):
    """Login form allowing username or email address."""
    username = forms.CharField(
        label='Username or Email Address',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter username or email address',
            'id': 'id_username',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'id': 'id_password',
            'autocomplete': 'current-password',
        })
    )


class RegisterForm(forms.ModelForm):
    """Public Sign Up / Registration Form. All accounts register as Employee by default."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email address (e.g. name@gmail.com)'}),
        label='Email Address'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm password',
        }),
        label='Confirm Password'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last name'}),
        }


    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        email = validate_email_format(email)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class ForgotPasswordForm(forms.Form):
    """Form for requesting a password reset email."""
    email = forms.EmailField(
        label='Registered Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your registered email address (e.g. user@gmail.com)',
            'id': 'id_email',
            'autocomplete': 'email',
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        email = validate_email_format(email)
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('No registered account was found with this email address.')
        return email


class ResetPasswordConfirmForm(forms.Form):
    """Form for setting a new password."""
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter new password',
            'id': 'id_new_password',
        })
    )
    new_password_confirm = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
            'id': 'id_new_password_confirm',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        password_confirm = cleaned_data.get('new_password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data



class UserForm(forms.ModelForm):
    """Form for creating a new user (Admin UI)."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter password',
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm password',
        }),
        label='Confirm Password'
    )
    role = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'employee']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'employee': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [('', '-- Select Role --')] + [
            (r.id, r.name) for r in Role.objects.all()
        ]
        self.fields['employee'].required = False

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class UserEditForm(forms.ModelForm):
    """Form for editing an existing user."""
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Leave blank to keep current',
        }),
        label='New Password'
    )
    role = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'employee', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'employee': forms.Select(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [('', '-- Select Role --')] + [
            (r.id, r.name) for r in Role.objects.all()
        ]
        self.fields['employee'].required = False


class RoleForm(forms.ModelForm):
    """Form for creating/editing roles."""
    class Meta:
        model = Role
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Role name'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Description'}),
        }


class RoleRequestForm(forms.Form):
    """Form for employees to request elevation to HR or Admin role."""
    requested_role = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Requested Role Privilege'
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': 'Explain why you need elevated HR or Admin privileges in the system...'
        }),
        label='Business Reason / Justification',
        help_text='Provide a clear justification. An Admin will review and verify your request.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only HR and Admin roles can be requested for elevation
        roles = Role.objects.filter(name__in=['HR', 'Admin']).order_by('name')
        self.fields['requested_role'].choices = [
            (r.id, f"{r.name} - {r.description or 'Privileged Access'}") for r in roles
        ]


class RoleRequestReviewForm(forms.Form):
    """Form for Admins to review and approve or reject a role elevation request."""
    action = forms.ChoiceField(
        choices=[
            ('approve', '✅ Approve & Grant Requested Role'),
            ('reject', '❌ Reject Request')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
        label='Review Decision'
    )
    admin_remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Add notes, reason for decision, or instructions for the employee...'
        }),
        label='Admin Remarks / Notes'
    )

