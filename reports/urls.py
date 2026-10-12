from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_view, name='reports'),
    path('generate/', views.generate_report_view, name='generate_report'),
    path('download/<int:export_id>/', views.download_report_view, name='download_report'),
    path('delete/<int:pk>/', views.delete_report_view, name='delete_report'),
]
