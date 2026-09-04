from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('create/', views.employee_create, name='employee_create'),
    path('import/', views.employee_bulk_import, name='employee_bulk_import'),
    path('<int:pk>/', views.employee_detail, name='employee_detail'),
    path('<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('profile/', views.my_profile, name='my_profile'),
    path('profile/edit/', views.edit_my_profile, name='edit_my_profile'),
]
