from django import forms
from .models import JobVacancy, CandidateCV
from .services.cv_extractor import validate_cv_file, CVExtractionError


class JobVacancyForm(forms.ModelForm):
    """Form for creating and editing Job Vacancies."""
    class Meta:
        model = JobVacancy
        fields = [
            'title', 'department', 'description', 'required_skills',
            'preferred_skills', 'required_experience_years',
            'educational_requirements', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Senior Full Stack Software Engineer'
            }),
            'department': forms.Select(attrs={
                'class': 'form-input'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Key responsibilities, team overview, and mission...'
            }),
            'required_skills': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Python, Django, PostgreSQL, REST APIs, Git'
            }),
            'preferred_skills': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Docker, AWS, Kubernetes, Celery, Redis'
            }),
            'required_experience_years': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'step': '1',
                'placeholder': 'e.g. 3'
            }),
            'educational_requirements': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. B.Sc. in Computer Science or equivalent'
            }),
            'status': forms.Select(attrs={
                'class': 'form-input'
            }),
        }


class CVUploadForm(forms.Form):
    """Form for uploading a candidate CV against a chosen Job Vacancy."""
    job_vacancy = forms.ModelChoiceField(
        queryset=JobVacancy.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-input',
            'id': 'id_job_vacancy'
        }),
        empty_label='-- Select Job Vacancy --'
    )
    cv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'id': 'id_cv_file',
            'accept': '.pdf,.docx'
        }),
        help_text='Accepts PDF or DOCX documents up to 5MB'
    )
    candidate_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Candidate full name (optional)'
        })
    )
    candidate_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'candidate@example.com (optional)'
        })
    )

    def clean_cv_file(self):
        cv_file = self.cleaned_data.get('cv_file')
        if cv_file:
            try:
                validate_cv_file(cv_file)
            except CVExtractionError as e:
                raise forms.ValidationError(str(e))
        return cv_file
