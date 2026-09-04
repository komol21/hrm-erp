"""
URL configuration for HRM ERP project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False)),
    path('django-admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.accounts.dashboard_urls')),
    path('organization/', include('apps.organization.urls')),
    path('employees/', include('apps.employees.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('leave/', include('apps.leave_management.urls')),
    path('payroll/', include('apps.payroll.urls')),
    path('recruitment/', include('apps.recruitment.urls')),
    path('api/hr/cv-analysis/', include('apps.recruitment.api_urls')),
    path('assistant/', include('apps.assistant.urls')),
]




if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
