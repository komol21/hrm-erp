from django.urls import path
from . import views
from . import firebase_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/done/', views.forgot_password_done_view, name='forgot_password_done'),
    path('reset-password/<str:uidb64>/<str:token>/', views.reset_password_confirm_view, name='reset_password_confirm'),

    # Firebase Authentication
    path('firebase/google-login/', firebase_views.firebase_google_login, name='firebase_google_login'),

    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    # Role elevation requests
    path('role-requests/', views.my_role_requests, name='my_role_requests'),
    path('admin/role-requests/', views.admin_role_request_list, name='admin_role_request_list'),
    path('admin/role-requests/<int:pk>/review/', views.admin_role_request_review, name='admin_role_request_review'),
]
