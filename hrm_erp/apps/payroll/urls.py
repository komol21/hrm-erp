from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    path('', views.payroll_list, name='payroll_list'),
    path('create/', views.payroll_create, name='payroll_create'),
    path('<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('<int:pk>/edit/', views.payroll_edit, name='payroll_edit'),
    path('<int:pk>/delete/', views.payroll_delete, name='payroll_delete'),
    path('my-payroll/', views.my_payroll, name='my_payroll'),
]
