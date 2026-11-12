import logging
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Count, Max
from crime_data.models import CrimeRecord

logger = logging.getLogger(__name__)


def get_crime_frequency_by_category(queryset):
    """
    Returns a dict {category_name: count} representing frequency distribution.
    """
    freq = (
        queryset.values('category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    return {item['category__name'] or 'Unknown': item['count'] for item in freq}


def get_monthly_trends(queryset, months=12):
    """
    Returns dict: {'labels': ['Jan 2024', ...], 'data': [12, 15, ...]}
    Anchors to the latest record date present in the dataset so historical records are accurately displayed.
    """
    if not queryset.exists():
        return {'labels': [], 'data': []}

    latest_date_agg = queryset.aggregate(Max('incident_date'))['incident_date__max']
    if latest_date_agg:
        end_date = datetime.combine(latest_date_agg, datetime.min.time())
    else:
        end_date = datetime.now()

    start_date = (end_date - relativedelta(months=months - 1)).replace(day=1)
    
    labels = []
    data = []

    for i in range(months):
        dt = start_date + relativedelta(months=i)
        label = dt.strftime('%b %Y')
        labels.append(label)

        m_start = dt.date()
        if dt.month == 12:
            m_end = datetime(dt.year + 1, 1, 1).date()
        else:
            m_end = datetime(dt.year, dt.month + 1, 1).date()

        cnt = queryset.filter(
            incident_date__gte=m_start,
            incident_date__lt=m_end
        ).count()
        data.append(cnt)

    return {
        'labels': labels,
        'data': data
    }


def get_yearly_trends(queryset):
    """
    Returns yearly crime aggregates: {'labels': ['2023', '2024'], 'data': [250, 310]}.
    """
    yearly = (
        queryset.values('incident_date__year')
        .annotate(count=Count('id'))
        .order_by('incident_date__year')
    )
    labels = [str(item['incident_date__year']) for item in yearly if item['incident_date__year']]
    data = [item['count'] for item in yearly if item['incident_date__year']]
    return {'labels': labels, 'data': data}


def get_location_counts(queryset, limit=8):
    """
    Returns dict {location_name: count} for top crime locations.
    """
    locs = (
        queryset.values('location__name', 'location__city')
        .annotate(count=Count('id'))
        .order_by('-count')[:limit]
    )
    result = {}
    for item in locs:
        name = item['location__name'] or 'Unknown'
        city = item['location__city']
        label = f"{name} ({city})" if city and city != name else name
        result[label] = item['count']
    return result


def get_severity_distribution(queryset):
    """
    Returns dict with count of incidents per severity level:
    {'Critical': count, 'High': count, 'Medium': count, 'Low': count}
    """
    return {
        'Critical': queryset.filter(severity='critical').count(),
        'High': queryset.filter(severity='high').count(),
        'Medium': queryset.filter(severity='medium').count(),
        'Low': queryset.filter(severity='low').count(),
    }


def get_category_comparison(queryset, location1_id, location2_id):
    """
    Compares crime frequency by category between two locations.
    """
    from crime_data.models import Location
    loc1 = Location.objects.filter(pk=location1_id).first()
    loc2 = Location.objects.filter(pk=location2_id).first()

    loc1_name = str(loc1) if loc1 else "Location 1"
    loc2_name = str(loc2) if loc2 else "Location 2"

    qs1 = queryset.filter(location_id=location1_id)
    qs2 = queryset.filter(location_id=location2_id)

    freq1 = get_crime_frequency_by_category(qs1)
    freq2 = get_crime_frequency_by_category(qs2)

    all_cats = sorted(list(set(freq1.keys()) | set(freq2.keys())))
    counts1 = [freq1.get(cat, 0) for cat in all_cats]
    counts2 = [freq2.get(cat, 0) for cat in all_cats]

    return {
        'categories': all_cats,
        'location1': {'name': loc1_name, 'counts': counts1},
        'location2': {'name': loc2_name, 'counts': counts2},
    }


def get_key_findings(queryset):
    """
    Analyzes the queryset and returns a list of human-readable text observations.
    """
    findings = []
    total = queryset.count()
    if total == 0:
        return ["No crime records available matching the criteria."]

    # Top category
    top_cat = (
        queryset.values('category__name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .first()
    )
    if top_cat:
        cat_pct = (top_cat['cnt'] / total) * 100
        findings.append(f"Top Crime Category: '{top_cat['category__name']}' accounts for {cat_pct:.1f}% ({top_cat['cnt']} incidents) of all records.")

    # Top location
    top_loc = (
        queryset.values('location__name', 'location__city')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .first()
    )
    if top_loc:
        loc_name = f"{top_loc['location__name']} ({top_loc['location__city']})"
        loc_pct = (top_loc['cnt'] / total) * 100
        findings.append(f"Primary Hotspot: {loc_name} reported the highest volume of activity with {top_loc['cnt']} incidents ({loc_pct:.1f}%).")

    # Severity distribution
    critical_count = queryset.filter(severity='critical').count()
    high_count = queryset.filter(severity='high').count()
    severe_pct = ((critical_count + high_count) / total) * 100 if total else 0
    findings.append(f"Severity Profile: {severe_pct:.1f}% of incidents are classified as High or Critical severity ({critical_count + high_count} cases).")

    # Solved rate
    solved_count = queryset.filter(status__in=['solved', 'closed']).count()
    solved_pct = (solved_count / total) * 100 if total else 0
    findings.append(f"Resolution Rate: {solved_pct:.1f}% of reported incidents have been resolved or closed ({solved_count} cases).")

    return findings
