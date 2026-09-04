from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.chat_page_view, name='chat'),
    path('api/send/', views.api_send_message, name='api_send_message'),
    path('api/clear/', views.api_clear_chat, name='api_clear_chat'),
]
