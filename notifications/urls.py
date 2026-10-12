from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_view, name='notifications'),
    path('mark-read/<int:pk>/', views.mark_read_view, name='mark_read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_read'),
    path('api/unread-count/', views.get_unread_count_view, name='get_unread_count'),
]
