"""
URL configuration for Crime Data Analysis Prediction System.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Custom error handlers — uses templates/errors/403.html, 404.html, 500.html
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('crime-data/', include('crime_data.urls')),
    path('analysis/', include('analysis.urls')),
    path('location/', include('location_analysis.urls')),
    path('patterns/', include('patterns.urls')),
    path('ontology/', include('ontology.urls')),
    path('model-training/', include('model_training.urls')),
    path('prediction/', include('prediction.urls')),
    path('visualization/', include('visualization.urls')),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

