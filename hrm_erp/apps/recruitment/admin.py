from django.contrib import admin
from .models import JobVacancy, Candidate, CandidateCV, CVAnalysis, MatchedSkill, MissingSkill


class MatchedSkillInline(admin.TabularInline):
    model = MatchedSkill
    extra = 0


class MissingSkillInline(admin.TabularInline):
    model = MissingSkill
    extra = 0


@admin.register(JobVacancy)
class JobVacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'required_experience_years', 'status', 'created_at')
    list_filter = ('status', 'department')
    search_fields = ('title', 'description', 'required_skills')


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'phone')


@admin.register(CandidateCV)
class CandidateCVAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_vacancy', 'candidate', 'file_name', 'file_size', 'uploaded_at')
    list_filter = ('job_vacancy', 'uploaded_at')


@admin.register(CVAnalysis)
class CVAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_cv', 'match_score', 'recommendation', 'created_at')
    list_filter = ('recommendation', 'created_at')
    inlines = [MatchedSkillInline, MissingSkillInline]
