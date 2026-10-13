from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('features/', views.features_view, name='features'),
    path('contact/', views.contact_view, name='contact'),
    path('api-docs/', views.api_docs_view, name='api_docs'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
]

