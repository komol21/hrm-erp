from django.db import models
from django.conf import settings
from apps.organization.models import Department


class JobVacancy(models.Model):
    """Job vacancy / role opening against which candidate CVs are analyzed."""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('draft', 'Draft'),
    ]

    title = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vacancies'
    )
    description = models.TextField(help_text='Job responsibilities and overview')
    required_skills = models.TextField(help_text='Comma-separated or bullet list of required skills')
    preferred_skills = models.TextField(blank=True, default='', help_text='Preferred or bonus skills')
    required_experience_years = models.PositiveIntegerField(
        default=0,
        help_text='Minimum years of experience required'
    )
    educational_requirements = models.TextField(
        blank=True,
        default='',
        help_text='Minimum education or degree requirements'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vacancies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'job_vacancies'
        ordering = ['-created_at']
        verbose_name = 'Job Vacancy'
        verbose_name_plural = 'Job Vacancies'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class Candidate(models.Model):
    """Candidate applicant profile."""
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recruitment_candidates'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class CandidateCV(models.Model):
    """Uploaded candidate CV file and its extracted text."""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='cvs',
        null=True,
        blank=True
    )
    job_vacancy = models.ForeignKey(
        JobVacancy,
        on_delete=models.CASCADE,
        related_name='candidate_cvs'
    )
    cv_file = models.FileField(upload_to='cv_uploads/')
    file_name = models.CharField(max_length=255, blank=True, default='')
    file_size = models.PositiveIntegerField(default=0, help_text='File size in bytes')
    extracted_text = models.TextField(blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'candidate_cvs'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"CV for {self.job_vacancy.title} - {self.file_name or self.id}"


class CVAnalysis(models.Model):
    """Structured AI analysis result for a candidate CV against a Job Vacancy."""
    RECOMMENDATION_CHOICES = [
        ('Strong Match', 'Strong Match'),
        ('Moderate Match', 'Moderate Match'),
        ('Weak Match', 'Weak Match'),
    ]

    candidate_cv = models.OneToOneField(
        CandidateCV,
        on_delete=models.CASCADE,
        related_name='analysis'
    )
    match_score = models.PositiveIntegerField(help_text='Overall Match Score 0-100%')
    recommendation = models.CharField(max_length=50, choices=RECOMMENDATION_CHOICES)
    experience_relevant_years = models.PositiveIntegerField(default=0)
    experience_meets_requirement = models.BooleanField(default=False)
    education_qualification = models.CharField(max_length=255, blank=True, default='')
    education_meets_requirement = models.BooleanField(default=False)
    strengths = models.JSONField(default=list, blank=True)
    missing_requirements = models.JSONField(default=list, blank=True)
    raw_json_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_analyses'
        ordering = ['-created_at']
        verbose_name = 'CV Analysis'
        verbose_name_plural = 'CV Analyses'

    def __str__(self):
        return f"Analysis: {self.candidate_cv.job_vacancy.title} - Score: {self.match_score}% ({self.recommendation})"


class MatchedSkill(models.Model):
    """Skills identified in the CV matching the Job Vacancy."""
    LEVEL_CHOICES = [
        ('Strong', 'Strong'),
        ('Moderate', 'Moderate'),
        ('Weak', 'Weak'),
    ]

    analysis = models.ForeignKey(
        CVAnalysis,
        on_delete=models.CASCADE,
        related_name='matched_skills'
    )
    skill = models.CharField(max_length=150)
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='Moderate')

    class Meta:
        db_table = 'cv_matched_skills'
        ordering = ['skill']

    def __str__(self):
        return f"{self.skill} ({self.level})"


class MissingSkill(models.Model):
    """Required/preferred skills missing or not demonstrated in the CV."""
    analysis = models.ForeignKey(
        CVAnalysis,
        on_delete=models.CASCADE,
        related_name='missing_skills'
    )
    skill = models.CharField(max_length=150)

    class Meta:
        db_table = 'cv_missing_skills'
        ordering = ['skill']

    def __str__(self):
        return self.skill
