import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from crime_data.models import CrimeRecord, CrimeCategory, Location
from analysis.utils import get_crime_frequency_by_category, get_monthly_trends, get_yearly_trends
from patterns.utils import identify_temporal_patterns

logger = logging.getLogger(__name__)


@login_required
def visualization_view(request):
    """
    Renders comprehensive data visualizations dashboard:
    - Doughnut chart: Category proportions
    - Multi-line chart: Monthly incident trends
    - Bar chart: Crime frequency by severity
    - Radar / Polar chart: Day of week distribution
    - Heatmap: Hourly distribution
    """
    categories = CrimeCategory.objects.all()
    locations = Location.objects.all()

    qs = CrimeRecord.objects.select_related('category', 'location').all()

    cat_freq = get_crime_frequency_by_category(qs)
    monthly_trends = get_monthly_trends(qs, months=12)
    yearly_trends = get_yearly_trends(qs)
    temporal_data = identify_temporal_patterns(qs)

    # Severity distribution
    severity_labels = ['Low', 'Medium', 'High', 'Critical']
    severity_counts = [
        qs.filter(severity='low').count(),
        qs.filter(severity='medium').count(),
        qs.filter(severity='high').count(),
        qs.filter(severity='critical').count(),
    ]

    context = {
        'categories': categories,
        'locations': locations,
        'cat_freq_json': json.dumps(cat_freq),
        'monthly_trends_json': json.dumps(monthly_trends),
        'yearly_trends_json': json.dumps(yearly_trends),
        'temporal_json': json.dumps(temporal_data),
        'severity_json': json.dumps({
            'labels': severity_labels,
            'data': severity_counts,
            'colors': ['#00E396', '#1769FF', '#FEB019', '#FF4560']
        }),
    }
    return render(request, 'visualization/visualization.html', context)


@login_required
def get_visualization_data_view(request):
    """
    AJAX endpoint for dynamically filtered chart data across categories, locations, and dates.
    """
    qs = CrimeRecord.objects.select_related('category', 'location').all()

    category_id = request.GET.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    location_id = request.GET.get('location')
    if location_id:
        qs = qs.filter(location_id=location_id)

    severity = request.GET.get('severity')
    if severity:
        qs = qs.filter(severity=severity)

    date_from = request.GET.get('date_from')
    if date_from:
        qs = qs.filter(incident_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        qs = qs.filter(incident_date__lte=date_to)

    cat_freq = get_crime_frequency_by_category(qs)
    monthly_trends = get_monthly_trends(qs, months=12)
    temporal = identify_temporal_patterns(qs)

    severity_counts = [
        qs.filter(severity='low').count(),
        qs.filter(severity='medium').count(),
        qs.filter(severity='high').count(),
        qs.filter(severity='critical').count(),
    ]

    return JsonResponse({
        'status': 'success',
        'category_freq': cat_freq,
        'monthly_trends': monthly_trends,
        'temporal': temporal,
        'severity': {
            'labels': ['Low', 'Medium', 'High', 'Critical'],
            'data': severity_counts
        },
        'total_count': qs.count()
    })
