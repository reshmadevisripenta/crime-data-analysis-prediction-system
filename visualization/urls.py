from django.urls import path
from . import views

app_name = 'visualization'

urlpatterns = [
    path('', views.visualization_view, name='visualize'),
    path('api/data/', views.get_visualization_data_view, name='get_data'),
    # Alias: visualization:visualization -> visualize
    path('visualization-alias/', views.visualization_view, name='visualization'),
]
