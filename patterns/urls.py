from django.urls import path
from . import views

app_name = 'patterns'

urlpatterns = [
    path('', views.patterns_view, name='patterns'),
]
