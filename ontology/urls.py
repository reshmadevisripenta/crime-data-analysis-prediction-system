from django.urls import path
from . import views

app_name = 'ontology'

urlpatterns = [
    path('', views.ontology_explorer_view, name='explorer'),
    path('api/graph-data/', views.get_graph_data_view, name='get_graph_data'),
    path('sparql/', views.sparql_query_view, name='sparql_query'),
    path('class/<str:class_name>/', views.class_detail_view, name='class_detail'),
]
