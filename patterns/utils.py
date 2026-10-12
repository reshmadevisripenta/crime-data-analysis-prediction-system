import logging
import pandas as pd
from datetime import datetime
from django.db.models import Count
from crime_data.models import CrimeRecord

logger = logging.getLogger(__name__)


def identify_temporal_patterns(queryset):
    """
    Computes temporal patterns:
    - Day of week distribution (Monday to Sunday)
    - Monthly seasonality (Jan to Dec)
    - Hourly distribution (00:00 to 23:00)
    """
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Day of week
    dow_counts = {name: 0 for name in day_names}
    # Monthly
    month_counts = {name: 0 for name in month_names}
    # Hourly
    hour_counts = {f"{h:02d}:00": 0 for h in range(24)}

    for incident_date, incident_time in queryset.values_list('incident_date', 'incident_time'):
        if incident_date:
            dow_idx = incident_date.weekday()
            dow_counts[day_names[dow_idx]] += 1

            m_idx = incident_date.month - 1
            month_counts[month_names[m_idx]] += 1

        if incident_time:
            h = incident_time.hour
            hour_counts[f"{h:02d}:00"] += 1

    return {
        'day_of_week': {
            'labels': list(dow_counts.keys()),
            'data': list(dow_counts.values())
        },
        'seasonality': {
            'labels': list(month_counts.keys()),
            'data': list(month_counts.values())
        },
        'hourly': {
            'labels': list(hour_counts.keys()),
            'data': list(hour_counts.values())
        }
    }


def identify_geographic_patterns(queryset):
    """
    Analyzes geographic clusters and hotspots by location and region type.
    """
    top_locations = (
        queryset.values('location__name', 'location__city', 'location__region_type')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )

    region_distribution = (
        queryset.values('location__region_type')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return {
        'top_locations': list(top_locations),
        'region_distribution': {
            'labels': [r['location__region_type'] or 'urban' for r in region_distribution],
            'data': [r['total'] for r in region_distribution]
        }
    }


def identify_category_patterns(queryset):
    """
    Computes category growth/decline rates comparing recent 6 months with prior 6 months.
    """
    now = datetime.now()
    records = queryset.values('category__name', 'incident_date')
    if not records:
        return {'growth_rates': [], 'labels': [], 'current': [], 'previous': []}

    df = pd.DataFrame(list(records))
    if df.empty or 'incident_date' not in df.columns:
        return {'growth_rates': [], 'labels': [], 'current': [], 'previous': []}

    df['incident_date'] = pd.to_datetime(df['incident_date'])
    midpoint = now - pd.Timedelta(days=180)
    startpoint = now - pd.Timedelta(days=360)

    recent_df = df[df['incident_date'] >= midpoint]
    prior_df = df[(df['incident_date'] >= startpoint) & (df['incident_date'] < midpoint)]

    recent_counts = recent_df['category__name'].value_counts()
    prior_counts = prior_df['category__name'].value_counts()

    all_cats = list(set(recent_counts.index) | set(prior_counts.index))
    growth_info = []

    for cat in all_cats:
        c_curr = int(recent_counts.get(cat, 0))
        c_prev = int(prior_counts.get(cat, 0))
        if c_prev > 0:
            rate = round(((c_curr - c_prev) / c_prev) * 100, 1)
        else:
            rate = 100.0 if c_curr > 0 else 0.0

        growth_info.append({
            'category': cat,
            'current_period': c_curr,
            'prior_period': c_prev,
            'growth_rate': rate
        })

    growth_info.sort(key=lambda x: x['growth_rate'], reverse=True)

    return {
        'growth_rates': growth_info,
        'labels': [g['category'] for g in growth_info],
        'current': [g['current_period'] for g in growth_info],
        'previous': [g['prior_period'] for g in growth_info]
    }


def calculate_statistical_observations(queryset):
    """
    Generates bulleted statistical observations and insights from pattern data.
    """
    observations = []
    total = queryset.count()
    if total == 0:
        return ["No sufficient crime data found to generate patterns."]

    temporal = identify_temporal_patterns(queryset)
    dow_data = temporal['day_of_week']
    if dow_data['data'] and max(dow_data['data']) > 0:
        max_idx = dow_data['data'].index(max(dow_data['data']))
        peak_day = dow_data['labels'][max_idx]
        observations.append(f"Peak Activity Day: {peak_day} exhibits highest crime frequency with {dow_data['data'][max_idx]} recorded incidents.")

    hourly_data = temporal['hourly']
    if hourly_data['data'] and max(hourly_data['data']) > 0:
        max_h_idx = hourly_data['data'].index(max(hourly_data['data']))
        peak_hour = hourly_data['labels'][max_h_idx]
        observations.append(f"Peak Time Window: Incidents cluster heavily around {peak_hour} hours.")

    cat_patterns = identify_category_patterns(queryset)
    if cat_patterns['growth_rates']:
        fastest = cat_patterns['growth_rates'][0]
        if fastest['growth_rate'] > 0:
            observations.append(f"Fastest Growing Category: '{fastest['category']}' shows an increase of {fastest['growth_rate']}% compared to previous period.")
        declining = [g for g in cat_patterns['growth_rates'] if g['growth_rate'] < 0]
        if declining:
            observations.append(f"Most Decreased Category: '{declining[-1]['category']}' dropped by {abs(declining[-1]['growth_rate'])}%.")

    geo_patterns = identify_geographic_patterns(queryset)
    if geo_patterns['top_locations']:
        top_l = geo_patterns['top_locations'][0]
        observations.append(f"Primary Focal Cluster: {top_l['location__name']} in {top_l['location__city']} represents the densest hot zone.")

    return observations
