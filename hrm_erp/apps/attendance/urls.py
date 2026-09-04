from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.attendance_list, name='attendance_list'),
    path('create/', views.attendance_create, name='attendance_create'),
    path('<int:pk>/edit/', views.attendance_edit, name='attendance_edit'),
    path('<int:pk>/delete/', views.attendance_delete, name='attendance_delete'),
    path('<int:pk>/comment/', views.hr_add_comment, name='hr_add_comment'),
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/', views.check_out, name='check_out'),
    path('my-attendance/', views.my_attendance, name='my_attendance'),
    path('policy/', views.attendance_policy_detail, name='attendance_policy_detail'),
    path('policy/edit/', views.attendance_policy_edit, name='attendance_policy_edit'),
]
