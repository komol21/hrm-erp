from django.urls import path
from . import dashboard_views as views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_redirect, name='redirect'),
    path('admin/', views.admin_dashboard, name='admin'),
    path('hr/', views.hr_dashboard, name='hr'),
    path('employee/', views.employee_dashboard, name='employee'),
    path('api/attendance-realtime/', views.attendance_realtime_api, name='attendance_realtime_api'),
]
