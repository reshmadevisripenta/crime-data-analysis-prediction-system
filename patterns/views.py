import json
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from crime_data.models import CrimeRecord, CrimeCategory, Location
from .models import CrimePattern
from .utils import (
    identify_temporal_patterns,
    identify_geographic_patterns,
    identify_category_patterns,
    calculate_statistical_observations
)

logger = logging.getLogger(__name__)


@login_required
def patterns_view(request):
    """
    Renders pattern analysis dashboard:
    - Temporal patterns (day of week, seasonality, hourly)
    - Category growth / decline
    - Geographic density
    - Summary analytical observations
    """
    qs = CrimeRecord.objects.select_related('category', 'location').all()

    # Filters
    category_id = request.GET.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    location_id = request.GET.get('location')
    if location_id:
        qs = qs.filter(location_id=location_id)

    temporal_data = identify_temporal_patterns(qs)
    geo_data = identify_geographic_patterns(qs)
    cat_data = identify_category_patterns(qs)
    observations = calculate_statistical_observations(qs)

    categories = CrimeCategory.objects.all()
    locations = Location.objects.all()
    saved_patterns = CrimePattern.objects.all().order_by('-identified_at')[:5]

    context = {
        'temporal_json': json.dumps(temporal_data),
        'geo_json': json.dumps(geo_data),
        'cat_json': json.dumps(cat_data),
        'observations': observations,
        'categories': categories,
        'locations': locations,
        'selected_category': category_id,
        'selected_location': location_id,
        'saved_patterns': saved_patterns,
    }
    return render(request, 'patterns/patterns.html', context)
