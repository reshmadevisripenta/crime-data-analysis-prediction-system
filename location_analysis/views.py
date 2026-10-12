import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from crime_data.models import CrimeRecord, CrimeCategory, Location
from .utils import get_map_markers, get_location_rankings, aggregate_by_location

logger = logging.getLogger(__name__)


@login_required
def map_view(request):
    """
    Renders the Leaflet interactive map page with initial markers and controls.
    """
    categories = CrimeCategory.objects.all()
    locations = Location.objects.all()

    qs = CrimeRecord.objects.select_related('location', 'category').all()
    markers = get_map_markers(qs)
    rankings = get_location_rankings(qs)[:10]

    context = {
        'categories': categories,
        'locations': locations,
        'markers_json': json.dumps(markers),
        'rankings': rankings,
        'total_hotspots': len(markers),
    }
    return render(request, 'location_analysis/map.html', context)


@login_required
def get_map_markers_view(request):
    """
    AJAX endpoint returning JSON marker list based on filter query parameters.
    """
    qs = CrimeRecord.objects.select_related('location', 'category').all()

    category_id = request.GET.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    severity = request.GET.get('severity')
    if severity:
        qs = qs.filter(severity=severity)

    date_from = request.GET.get('date_from')
    if date_from:
        qs = qs.filter(incident_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        qs = qs.filter(incident_date__lte=date_to)

    markers = get_map_markers(qs)
    rankings = get_location_rankings(qs)[:10]
    aggregated = aggregate_by_location(qs)[:10]

    return JsonResponse({
        'status': 'success',
        'markers': markers,
        'rankings': rankings,
        'aggregated': aggregated,
        'count': len(markers),
    })
