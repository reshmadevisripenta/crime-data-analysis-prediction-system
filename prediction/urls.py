from django.urls import path
from . import views

app_name = 'prediction'

urlpatterns = [
    path('', views.prediction_view, name='prediction'),
    path('run/', views.run_prediction_view, name='run_prediction'),
    path('forecast/', views.run_prediction_view, name='forecast'),
]
