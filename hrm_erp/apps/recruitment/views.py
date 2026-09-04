from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
import re

from apps.accounts.permissions import hr_required, role_required
from .models import JobVacancy, Candidate, CandidateCV, CVAnalysis, MatchedSkill, MissingSkill
from .forms import JobVacancyForm, CVUploadForm
from .services.cv_extractor import (
    extract_cv_text,
    CVExtractionError,
    extract_candidate_name_from_filename,
    extract_candidate_email_from_text,
)
from .services.ai_analyzer import analyze_cv_with_ai


def process_single_cv(vacancy, cv_file, cand_name='', cand_email=''):
    """
    Extract CV text, run AI analysis against target vacancy, and persist all records.
    Returns: dictionary with analysis metadata and structured AI output.
    """
    # 1. Extract CV Text
    extracted_text = extract_cv_text(cv_file)

    # Auto-extract name & email if omitted
    if not cand_name:
        cand_name = extract_candidate_name_from_filename(cv_file.name)
    if not cand_email:
        cand_email = extract_candidate_email_from_text(extracted_text)

    # 2. Run AI Analysis
    ai_data = analyze_cv_with_ai(vacancy, extracted_text)

    # 3. Save to database in a transaction
    with transaction.atomic():
        candidate = None
        if cand_name or cand_email:
            email_key = cand_email or f"{re.sub(r'[^a-zA-Z0-9]', '', cand_name.lower())}@applicant.local"
            candidate, _ = Candidate.objects.get_or_create(
                email=email_key,
                defaults={'name': cand_name or 'Applicant'}
            )

        candidate_cv = CandidateCV.objects.create(
            candidate=candidate,
            job_vacancy=vacancy,
            cv_file=cv_file,
            file_name=cv_file.name,
            file_size=cv_file.size,
            extracted_text=extracted_text
        )

        analysis = CVAnalysis.objects.create(
            candidate_cv=candidate_cv,
            match_score=ai_data['match_score'],
            recommendation=ai_data['recommendation'],
            experience_relevant_years=ai_data.get('experience', {}).get('relevant_years', 0),
            experience_meets_requirement=ai_data.get('experience', {}).get('meets_requirement', False),
            education_qualification=ai_data.get('education', {}).get('qualification', ''),
            education_meets_requirement=ai_data.get('education', {}).get('meets_requirement', False),
            strengths=ai_data.get('strengths', []),
            missing_requirements=ai_data.get('missing_requirements', []),
            raw_json_response=ai_data
        )

        # Save matched skills
        for item in ai_data.get('matched_skills', []):
            MatchedSkill.objects.create(
                analysis=analysis,
                skill=item.get('skill', ''),
                level=item.get('level', 'Moderate')
            )

        # Save missing skills
        for skill_name in ai_data.get('missing_skills', []):
            MissingSkill.objects.create(
                analysis=analysis,
                skill=skill_name
            )

    return {
        'analysis_id': analysis.id,
        'job_title': vacancy.title,
        'candidate_name': cand_name or (candidate.name if candidate else 'Applicant'),
        'candidate_email': cand_email,
        'file_name': cv_file.name,
        'file_size': cv_file.size,
        'match_score': analysis.match_score,
        'recommendation': analysis.recommendation,
        'experience_years': analysis.experience_relevant_years,
        'experience_meets': analysis.experience_meets_requirement,
        'education_qualification': analysis.education_qualification,
        'education_meets': analysis.education_meets_requirement,
        'matched_skills_count': len(ai_data.get('matched_skills', [])),
        'missing_skills_count': len(ai_data.get('missing_skills', [])),
        'result': ai_data,
        'analysis_obj': analysis,
    }


# ─── Job Vacancy CRUD ─────────────────────────────────────────────────────────

@login_required
@role_required('Admin', 'HR')
def vacancy_list(request):
    """List all job vacancies."""
    vacancies = JobVacancy.objects.select_related('department', 'created_by').all()
    status_filter = request.GET.get('status', '')
    if status_filter in ['open', 'closed', 'draft']:
        vacancies = vacancies.filter(status=status_filter)

    paginator = Paginator(vacancies, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/vacancy_list.html', {
        'vacancies': page_obj,
        'status_filter': status_filter,
        'page_title': 'Job Vacancies',
    })


@login_required
@hr_required
def vacancy_create(request):
    """Create a new job vacancy."""
    if request.method == 'POST':
        form = JobVacancyForm(request.POST)
        if form.is_valid():
            vacancy = form.save(commit=False)
            vacancy.created_by = request.user
            vacancy.save()
            messages.success(request, f"Job vacancy '{vacancy.title}' created successfully.")
            return redirect('recruitment:vacancy_list')
    else:
        form = JobVacancyForm()

    return render(request, 'recruitment/vacancy_form.html', {
        'form': form,
        'page_title': 'Create Job Vacancy',
        'is_edit': False,
    })


@login_required
@hr_required
def vacancy_edit(request, pk):
    """Edit an existing job vacancy."""
    vacancy = get_object_or_404(JobVacancy, pk=pk)
    if request.method == 'POST':
        form = JobVacancyForm(request.POST, instance=vacancy)
        if form.is_valid():
            form.save()
            messages.success(request, f"Job vacancy '{vacancy.title}' updated successfully.")
            return redirect('recruitment:vacancy_list')
    else:
        form = JobVacancyForm(instance=vacancy)

    return render(request, 'recruitment/vacancy_form.html', {
        'form': form,
        'vacancy': vacancy,
        'page_title': f"Edit Vacancy: {vacancy.title}",
        'is_edit': True,
    })


@login_required
@hr_required
def vacancy_delete(request, pk):
    """Delete a job vacancy."""
    vacancy = get_object_or_404(JobVacancy, pk=pk)
    if request.method == 'POST':
        title = vacancy.title
        vacancy.delete()
        messages.success(request, f"Job vacancy '{title}' deleted successfully.")
        return redirect('recruitment:vacancy_list')

    return render(request, 'components/confirm_delete.html', {
        'object': vacancy,
        'object_name': vacancy.title,
        'page_title': f"Delete Vacancy: {vacancy.title}",
        'cancel_url': 'recruitment:vacancy_list',
    })


# ─── AI CV Analysis Views ───────────────────────────────────────────────────

@login_required
@role_required('Admin', 'HR')
def cv_analysis_view(request):
    """Main interactive page for HR to upload CVs and view real-time AI evaluations."""
    vacancies = JobVacancy.objects.filter(status='open')
    selected_vacancy_id = request.GET.get('vacancy_id', '')
    selected_vacancy = None
    if selected_vacancy_id:
        selected_vacancy = JobVacancy.objects.filter(pk=selected_vacancy_id).first()

    analysis_result = None
    form = CVUploadForm(initial={'job_vacancy': selected_vacancy} if selected_vacancy else None)

    # If submitted via standard POST form (non-AJAX)
    if request.method == 'POST':
        form = CVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            vacancy = form.cleaned_data['job_vacancy']
            cv_file = form.cleaned_data['cv_file']
            cand_name = form.cleaned_data.get('candidate_name', '')
            cand_email = form.cleaned_data.get('candidate_email', '')

            try:
                data = process_single_cv(vacancy, cv_file, cand_name, cand_email)
                analysis_result = data.get('analysis_obj')
                messages.success(request, f"CV Analysis complete! Match Score: {analysis_result.match_score}% ({analysis_result.recommendation})")
            except CVExtractionError as e:
                messages.error(request, f"CV File Error: {str(e)}")
            except Exception as e:
                messages.error(request, f"Analysis Error: {str(e)}")

    recent_analyses = CVAnalysis.objects.select_related('candidate_cv__job_vacancy', 'candidate_cv__candidate')[:5]

    return render(request, 'recruitment/cv_analysis.html', {
        'form': form,
        'vacancies': vacancies,
        'selected_vacancy': selected_vacancy,
        'analysis': analysis_result,
        'recent_analyses': recent_analyses,
        'page_title': 'AI-Powered CV Analysis & Job Matching',
    })


@login_required
@require_POST
def api_cv_analysis(request):
    """
    JSON API endpoint for single CV analysis.
    Endpoint: POST /api/hr/cv-analysis/
    """
    if not (request.user.is_admin() or request.user.is_hr()):
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized: Only HR and Admin users can access AI CV Analysis.'
        }, status=403)

    vacancy_id = request.POST.get('job_vacancy') or request.POST.get('job_vacancy_id')
    if not vacancy_id:
        return JsonResponse({'success': False, 'error': 'Please select a job vacancy.'}, status=400)

    try:
        vacancy = JobVacancy.objects.get(pk=vacancy_id)
    except JobVacancy.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Selected job vacancy not found.'}, status=404)

    cv_file = request.FILES.get('cv_file')
    if not cv_file:
        return JsonResponse({'success': False, 'error': 'Please upload a candidate CV file (PDF or DOCX).'}, status=400)

    cand_name = request.POST.get('candidate_name', '').strip()
    cand_email = request.POST.get('candidate_email', '').strip()

    try:
        data = process_single_cv(vacancy, cv_file, cand_name, cand_email)
        # Exclude internal non-serializable object
        data.pop('analysis_obj', None)
        return JsonResponse({'success': True, **data})
    except CVExtractionError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Analysis failed: {str(e)}"}, status=500)


@login_required
@require_POST
def api_batch_cv_analysis(request):
    """
    JSON API endpoint for Batch / Multiple CV analysis.
    Endpoint: POST /api/hr/cv-analysis/batch/
    Accepts: job_vacancy (ID) and cv_files (multiple files)
    Returns: Ranked candidate comparison results sorted by Match Score descending.
    """
    if not (request.user.is_admin() or request.user.is_hr()):
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized: Only HR and Admin users can access AI CV Analysis.'
        }, status=403)

    vacancy_id = request.POST.get('job_vacancy') or request.POST.get('job_vacancy_id')
    if not vacancy_id:
        return JsonResponse({'success': False, 'error': 'Please select a job vacancy.'}, status=400)

    try:
        vacancy = JobVacancy.objects.get(pk=vacancy_id)
    except JobVacancy.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Selected job vacancy not found.'}, status=404)

    files = request.FILES.getlist('cv_files') or request.FILES.getlist('cv_files[]')
    if not files:
        single = request.FILES.get('cv_file')
        if single:
            files = [single]
        else:
            return JsonResponse({'success': False, 'error': 'Please upload at least one candidate CV file.'}, status=400)

    results = []
    errors = []

    for f in files:
        try:
            item = process_single_cv(vacancy, f)
            item.pop('analysis_obj', None)
            results.append(item)
        except Exception as e:
            errors.append({'file_name': f.name, 'error': str(e)})

    # Sort results by match score descending (highest rank first)
    results.sort(key=lambda x: x.get('match_score', 0), reverse=True)

    return JsonResponse({
        'success': True,
        'job_title': vacancy.title,
        'total_processed': len(results),
        'total_failed': len(errors),
        'results': results,
        'errors': errors,
    })


@login_required
@role_required('Admin', 'HR')
def analysis_detail_view(request, pk):
    """View details of a previous CV analysis report."""
    analysis = get_object_or_404(
        CVAnalysis.objects.select_related('candidate_cv__job_vacancy', 'candidate_cv__candidate'),
        pk=pk
    )
    matched_skills = analysis.matched_skills.all()
    missing_skills = analysis.missing_skills.all()

    return render(request, 'recruitment/analysis_detail.html', {
        'analysis': analysis,
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'page_title': f"CV Analysis: {analysis.candidate_cv.job_vacancy.title}",
    })


@login_required
@role_required('Admin', 'HR')
def analysis_history_view(request):
    """View list of all past candidate CV analyses."""
    analyses = CVAnalysis.objects.select_related(
        'candidate_cv__job_vacancy', 'candidate_cv__candidate'
    ).all()

    # Search & filters
    vacancy_filter = request.GET.get('vacancy', '')
    rec_filter = request.GET.get('recommendation', '')
    
    if vacancy_filter:
        analyses = analyses.filter(candidate_cv__job_vacancy_id=vacancy_filter)
    if rec_filter:
        analyses = analyses.filter(recommendation=rec_filter)

    paginator = Paginator(analyses, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    vacancies = JobVacancy.objects.all()

    return render(request, 'recruitment/analysis_history.html', {
        'analyses': page_obj,
        'vacancies': vacancies,
        'vacancy_filter': vacancy_filter,
        'rec_filter': rec_filter,
        'page_title': 'CV Analysis History',
    })
