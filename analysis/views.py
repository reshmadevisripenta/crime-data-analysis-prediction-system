import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from accounts.decorators import analyst_required
from crime_data.models import CrimeRecord, CrimeCategory, Location, DatasetUpload
from model_training.models import MLModel
from .models import AnalysisResult, TrendData
from .utils import (
    get_crime_frequency_by_category,
    get_monthly_trends,
    get_yearly_trends,
    get_location_counts,
    get_severity_distribution,
    get_category_comparison,
    get_key_findings
)

logger = logging.getLogger(__name__)


def _filter_analysis_queryset(request):
    """Applies filter parameters to the CrimeRecord queryset."""
    qs = CrimeRecord.objects.select_related('category', 'location').all()

    category_id = request.GET.get('category')
    if category_id:
        if category_id.isdigit():
            qs = qs.filter(category_id=int(category_id))
        else:
            qs = qs.filter(category__name__iexact=category_id)

    location_id = request.GET.get('location')
    if location_id:
        if location_id.isdigit():
            qs = qs.filter(location_id=int(location_id))
        else:
            qs = qs.filter(location__name__icontains=location_id)

    city = request.GET.get('city')
    if city:
        qs = qs.filter(location__city__iexact=city)

    severity = request.GET.get('severity')
    if severity:
        qs = qs.filter(severity=severity.lower())

    date_from = request.GET.get('date_from')
    if date_from:
        qs = qs.filter(incident_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        qs = qs.filter(incident_date__lte=date_to)

    return qs


@login_required
def analysis_view(request):
    """
    Main analysis dashboard. Renders filter controls and initial analysis findings.
    """
    categories = CrimeCategory.objects.all()
    locations = Location.objects.all()
    cities = Location.objects.exclude(city='').values_list('city', flat=True).distinct().order_by('city')

    # Apply any initial GET filters if present
    qs = _filter_analysis_queryset(request)

    category_freq = get_crime_frequency_by_category(qs)
    monthly_trends = get_monthly_trends(qs, months=12)
    yearly_trends = get_yearly_trends(qs)
    location_counts = get_location_counts(qs)
    severity_stats = get_severity_distribution(qs)
    findings = get_key_findings(qs)

    past_analyses = AnalysisResult.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    trained_models_count = MLModel.objects.filter(status='trained').count()
    has_trained_model = trained_models_count > 0

    context = {
        'categories': categories,
        'locations': locations,
        'cities': cities,
        'severities': [
            ('low', 'Low Severity'),
            ('medium', 'Medium Severity'),
            ('high', 'High Severity'),
            ('critical', 'Critical Severity')
        ],
        'category_freq_json': json.dumps(category_freq),
        'monthly_trends_json': json.dumps(monthly_trends),
        'yearly_trends_json': json.dumps(yearly_trends),
        'location_counts_json': json.dumps(location_counts),
        'severity_stats_json': json.dumps(severity_stats),
        'findings': findings,
        'past_analyses': past_analyses,
        'total_records': qs.count(),
        'selected_location': request.GET.get('location', ''),
        'selected_category': request.GET.get('category', ''),
        'selected_severity': request.GET.get('severity', ''),
        'selected_date_from': request.GET.get('date_from', ''),
        'selected_date_to': request.GET.get('date_to', ''),
        'trained_models_count': trained_models_count,
        'has_trained_model': has_trained_model,
    }
    return render(request, 'analysis/analysis.html', context)


@login_required
def get_analysis_data_view(request):
    """
    AJAX endpoint: dynamically computes and returns chart JSON data
    based on filters (category, location, city, severity, date_from, date_to).
    """
    qs = _filter_analysis_queryset(request)

    category_freq = get_crime_frequency_by_category(qs)
    monthly_trends = get_monthly_trends(qs, months=12)
    yearly_trends = get_yearly_trends(qs)
    location_counts = get_location_counts(qs)
    severity_stats = get_severity_distribution(qs)
    findings = get_key_findings(qs)

    loc1 = request.GET.get('compare_loc1')
    loc2 = request.GET.get('compare_loc2')
    comparison = None
    if loc1 and loc2:
        comparison = get_category_comparison(CrimeRecord.objects.all(), loc1, loc2)

    return JsonResponse({
        'status': 'success',
        'category_freq': category_freq,
        'monthly_trends': monthly_trends,
        'yearly_trends': yearly_trends,
        'location_counts': location_counts,
        'severity_stats': severity_stats,
        'findings': findings,
        'comparison': comparison,
        'total_records': qs.count()
    })


@analyst_required
@require_POST
def run_analysis_view(request):
    """
    Runs a formal analysis job and saves results to the database as AnalysisResult.
    """
    name = request.POST.get('name', 'Ad-hoc Analysis')
    analysis_type = request.POST.get('analysis_type', 'frequency')
    dataset_id = request.POST.get('dataset_id')

    qs = CrimeRecord.objects.all()
    if dataset_id:
        qs = qs.filter(dataset_upload_id=dataset_id)

    category_freq = get_crime_frequency_by_category(qs)
    monthly_trends = get_monthly_trends(qs)
    findings = get_key_findings(qs)

    dataset = DatasetUpload.objects.filter(pk=dataset_id).first() if dataset_id else None

    result = AnalysisResult.objects.create(
        name=name,
        analysis_type=analysis_type,
        dataset=dataset,
        parameters={'dataset_id': dataset_id, 'type': analysis_type},
        results={
            'category_freq': category_freq,
            'monthly_trends': monthly_trends,
            'total': qs.count()
        },
        summary="\n".join(findings),
        created_by=request.user
    )

    # Save trend data points
    trend_labels = monthly_trends.get('labels', [])
    trend_counts = monthly_trends.get('data', [])
    for p, c in zip(trend_labels, trend_counts):
        TrendData.objects.create(
            analysis=result,
            period=p,
            crime_count=c,
            period_type='monthly'
        )

    return JsonResponse({
        'status': 'success',
        'id': result.id,
        'name': result.name,
        'message': f"Analysis '{result.name}' saved successfully."
    })
