from django.urls import path
from . import views

app_name = 'crime_data'

urlpatterns = [
    path('', views.crime_record_list_view, name='record_list_default'),
    path('records/', views.crime_record_list_view, name='record_list'),
    path('records/create/', views.crime_record_create_view, name='record_create'),
    path('records/<int:pk>/', views.crime_record_detail_view, name='record_detail'),
    path('records/<int:pk>/edit/', views.crime_record_update_view, name='record_update'),
    path('records/<int:pk>/delete/', views.crime_record_delete_view, name='record_delete'),
    path('upload/', views.dataset_upload_view, name='upload_dataset'),
    path('preview/<int:pk>/', views.dataset_preview_view, name='dataset_preview'),
    path('download/<int:pk>/', views.download_cleaned_dataset_view, name='download_cleaned'),
    path('delete-dataset/<int:pk>/', views.delete_dataset_view, name='delete_dataset'),
    # Aliases for backwards-compat with tests and templates
    path('upload-alias/', views.dataset_upload_view, name='upload'),
    path('records-alias/', views.crime_record_list_view, name='records_list'),
    path('list-alias/', views.crime_record_list_view, name='list'),
]
