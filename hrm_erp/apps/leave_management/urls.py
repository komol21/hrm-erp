from django.urls import path
from . import views

app_name = 'leave'

urlpatterns = [
    # Leave Types (Admin/HR)
    path('types/', views.leave_type_list, name='type_list'),
    path('types/create/', views.leave_type_create, name='type_create'),
    path('types/<int:pk>/edit/', views.leave_type_edit, name='type_edit'),
    path('types/<int:pk>/delete/', views.leave_type_delete, name='type_delete'),
    # Leave Requests
    path('requests/', views.leave_request_list, name='request_list'),
    path('requests/create/', views.leave_request_create, name='request_create'),
    path('requests/<int:pk>/', views.leave_request_detail, name='request_detail'),
    path('requests/<int:pk>/review/', views.leave_request_review, name='request_review'),
    path('my-leaves/', views.my_leaves, name='my_leaves'),
]
