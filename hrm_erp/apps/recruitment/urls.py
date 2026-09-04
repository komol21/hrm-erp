from django.urls import path
from . import views

app_name = 'recruitment'

urlpatterns = [
    # Job Vacancies
    path('vacancies/', views.vacancy_list, name='vacancy_list'),
    path('vacancies/create/', views.vacancy_create, name='vacancy_create'),
    path('vacancies/<int:pk>/edit/', views.vacancy_edit, name='vacancy_edit'),
    path('vacancies/<int:pk>/delete/', views.vacancy_delete, name='vacancy_delete'),

    # AI CV Analysis
    path('cv-analysis/', views.cv_analysis_view, name='cv_analysis'),
    path('cv-analysis/<int:pk>/', views.analysis_detail_view, name='analysis_detail'),
    path('history/', views.analysis_history_view, name='analysis_history'),

    # Backend AJAX API endpoints
    path('api/cv-analysis/', views.api_cv_analysis, name='api_cv_analysis'),
    path('api/cv-analysis/batch/', views.api_batch_cv_analysis, name='api_batch_cv_analysis'),
]
