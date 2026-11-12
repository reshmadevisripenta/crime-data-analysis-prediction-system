from django.urls import path
from . import views

app_name = 'model_training'

urlpatterns = [
    path('', views.model_training_view, name='train'),
    path('training-view/', views.model_training_view, name='training'),
    path('train/', views.train_model_view, name='run_training'),
    path('models/', views.model_list_view, name='model_list'),
    path('models/<int:pk>/', views.model_detail_view, name='model_detail'),
    path('models/<int:pk>/delete/', views.delete_model_view, name='delete_model'),
]
