from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_cv_analysis, name='api_cv_analysis_root'),
    path('batch/', views.api_batch_cv_analysis, name='api_batch_cv_analysis_root'),
]
