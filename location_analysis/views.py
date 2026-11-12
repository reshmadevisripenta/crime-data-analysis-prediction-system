import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from crime_data.models import CrimeRecord, CrimeCategory, Location
from .utils import (
    get_map_markers,
    get_location_rankings,
    aggregate_by_location,
    aggregate_by_city
)

logger = logging.getLogger(__name__)


def _filter_crime_queryset(request):
    """Helper to apply query parameters to CrimeRecord queryset."""
    qs = CrimeRecord.objects.select_related('location', 'category').all()

    category_id = request.GET.get('category')
    if category_id:
        if category_id.isdigit():
            qs = qs.filter(category_id=int(category_id))
        else:
            qs = qs.filter(category__name__iexact=category_id)

    city = request.GET.get('city')
    if city:
        qs = qs.filter(location__city__iexact=city)

    severity = request.GET.get('severity')
    if severity:
        qs = qs.filter(severity=severity.lower())

    region_type = request.GET.get('region_type')
    if region_type:
        qs = qs.filter(location__region_type=region_type.lower())

    date_from = request.GET.get('date_from')
    if date_from:
        qs = qs.filter(incident_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        qs = qs.filter(incident_date__lte=date_to)

    return qs


@login_required
def map_view(request):
    """
    Renders the Leaflet interactive map page with real dataset records,
    working filters (city, category, severity, date range), and live location statistics.
    """
    qs = _filter_crime_queryset(request)

    categories = CrimeCategory.objects.all()
    cities = Location.objects.exclude(city='').values_list('city', flat=True).distinct().order_by('city')
    
    markers = get_map_markers(qs)
    rankings = get_location_rankings(qs)
    location_stats = aggregate_by_location(qs)
    city_stats = aggregate_by_city(qs)

    context = {
        'categories': categories,
        'cities': cities,
        'severities': [
            ('low', 'Low Severity'),
            ('medium', 'Medium Severity'),
            ('high', 'High Severity'),
            ('critical', 'Critical Severity')
        ],
        'region_types': Location.REGION_CHOICES,
        'markers_json': json.dumps(markers),
        'rankings': rankings,
        'top_hotspots': rankings[:5],
        'location_stats': location_stats,
        'city_stats': city_stats,
        'total_hotspots': len(markers),
        'total_cases': qs.count(),
        'total_locations_count': len(location_stats),
        'selected_category': request.GET.get('category', ''),
        'selected_city': request.GET.get('city', ''),
        'selected_severity': request.GET.get('severity', ''),
        'selected_region_type': request.GET.get('region_type', ''),
        'selected_date_from': request.GET.get('date_from', ''),
        'selected_date_to': request.GET.get('date_to', ''),
    }
    return render(request, 'location_analysis/map.html', context)


@login_required
def get_map_markers_view(request):
    """
    AJAX endpoint returning JSON marker list based on filter query parameters.
    """
    qs = _filter_crime_queryset(request)

    markers = get_map_markers(qs)
    rankings = get_location_rankings(qs)[:10]
    location_stats = aggregate_by_location(qs)
    city_stats = aggregate_by_city(qs)

    return JsonResponse({
        'status': 'success',
        'markers': markers,
        'rankings': rankings,
        'location_stats': location_stats,
        'city_stats': city_stats,
        'count': len(markers),
        'total_cases': qs.count(),
    })
