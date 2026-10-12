from django.urls import path
from . import views

app_name = 'location_analysis'

urlpatterns = [
    path('', views.map_view, name='map'),
    path('api/markers/', views.get_map_markers_view, name='get_markers'),
]
