from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.analysis_view, name='analysis'),
    path('api/data/', views.get_analysis_data_view, name='get_analysis_data'),
    path('run/', views.run_analysis_view, name='run_analysis'),
]
