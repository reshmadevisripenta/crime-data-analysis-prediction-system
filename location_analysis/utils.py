import logging
from collections import defaultdict
from django.db.models import Count, Q
from crime_data.models import Location, CrimeRecord

logger = logging.getLogger(__name__)


def get_map_markers(queryset):
    """
    Transforms crime records / locations into marker data objects for Leaflet.js:
    [{'id': int, 'title': str, 'city': str, 'lat': float, 'lng': float,
      'count': int, 'category': str, 'color': str, 'region_type': str}]
    Single grouped query with zero N+1 latency.
    """
    loc_stats = (
        queryset.values(
            'location_id',
            'location__name',
            'location__city',
            'location__state',
            'location__latitude',
            'location__longitude',
            'location__region_type',
        )
        .annotate(
            crime_count=Count('id'),
            critical_cnt=Count('id', filter=Q(severity='critical')),
            high_cnt=Count('id', filter=Q(severity='high')),
            med_cnt=Count('id', filter=Q(severity='medium')),
            low_cnt=Count('id', filter=Q(severity='low')),
        )
        .order_by('-crime_count')
    )

    # Pre-fetch top category per location in one query
    top_cats_qs = (
        queryset.values('location_id', 'category__name')
        .annotate(cnt=Count('id'))
        .order_by('location_id', '-cnt')
    )
    top_cat_map = {}
    for tc in top_cats_qs:
        loc_id = tc['location_id']
        if loc_id not in top_cat_map:
            top_cat_map[loc_id] = tc['category__name'] or 'General'

    markers = []
    for stat in loc_stats:
        raw_lat = stat['location__latitude']
        raw_lng = stat['location__longitude']
        if raw_lat is None or raw_lng is None:
            continue

        try:
            lat = float(raw_lat)
            lng = float(raw_lng)
        except (ValueError, TypeError):
            continue

        # Strict coordinate validation: only real geographic coordinates
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            continue

        loc_id = stat['location_id']
        cat_name = top_cat_map.get(loc_id, 'General')
        count = stat['crime_count']
        crit_cnt = stat['critical_cnt']
        high_cnt = stat['high_cnt']
        med_cnt = stat['med_cnt']
        low_cnt = stat['low_cnt']

        # Determine severity-based hotspot color and risk tier
        if crit_cnt >= 5 or count >= 30:
            color = '#EF4444'  # Critical / High density danger red
            severity_tier = 'Critical Risk'
        elif crit_cnt >= 1 or high_cnt >= 5 or count >= 15:
            color = '#F59E0B'  # High severity warning amber
            severity_tier = 'High Risk'
        elif med_cnt >= 5 or count >= 5:
            color = '#3B82F6'  # Moderate risk blue
            severity_tier = 'Moderate Risk'
        else:
            color = '#10B981'  # Low severity / density green
            severity_tier = 'Low Risk'

        markers.append({
            'id': loc_id,
            'title': stat['location__name'],
            'city': stat['location__city'],
            'state': stat['location__state'],
            'lat': lat,
            'lng': lng,
            'count': count,
            'critical_cnt': crit_cnt,
            'high_cnt': high_cnt,
            'med_cnt': med_cnt,
            'low_cnt': low_cnt,
            'severity_tier': severity_tier,
            'category': cat_name,
            'color': color,
            'region_type': stat['location__region_type'] or 'urban',
        })

    return markers


def get_location_rankings(queryset):
    """
    Returns ranked list of locations ordered by incident frequency.
    """
    rankings = (
        queryset.values(
            'location__id',
            'location__name',
            'location__city',
            'location__state',
            'location__region_type'
        )
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    return list(rankings)


def aggregate_by_location(queryset):
    """
    Groups crime records by location with breakdown by severity, top category, and resolution.
    Uses conditional aggregation to eliminate N+1 queries.
    """
    locations = (
        queryset.values(
            'location__id',
            'location__name',
            'location__city',
            'location__state',
            'location__latitude',
            'location__longitude',
            'location__region_type',
        )
        .annotate(
            total=Count('id'),
            critical_cnt=Count('id', filter=Q(severity='critical')),
            high_cnt=Count('id', filter=Q(severity='high')),
            med_cnt=Count('id', filter=Q(severity='medium')),
            low_cnt=Count('id', filter=Q(severity='low')),
            solved_cnt=Count('id', filter=Q(status__in=['solved', 'closed'])),
        )
        .order_by('-total')
    )

    # Pre-fetch category breakdowns per location in a single pass
    cat_counts_qs = (
        queryset.values('location_id', 'category__name')
        .annotate(cnt=Count('id'))
        .order_by('location_id', '-cnt')
    )
    loc_cats_map = defaultdict(list)
    for c in cat_counts_qs:
        loc_cats_map[c['location_id']].append(f"{c['category__name']}: {c['cnt']}")

    aggregated = []
    for item in locations:
        loc_id = item['location__id']
        total = item['total']
        critical_cnt = item['critical_cnt']
        solved_cnt = item['solved_cnt']

        cat_list = loc_cats_map.get(loc_id, [])
        top_cat = cat_list[0].split(':')[0] if cat_list else 'N/A'
        categories_summary = ", ".join(cat_list[:3])

        if total >= 50 or critical_cnt >= 10:
            risk_tier = 'Critical'
            risk_badge = 'danger'
        elif total >= 25 or critical_cnt >= 5:
            risk_tier = 'High Risk'
            risk_badge = 'danger-subtle text-danger'
        elif total >= 10:
            risk_tier = 'Moderate'
            risk_badge = 'warning-subtle text-warning'
        else:
            risk_tier = 'Low'
            risk_badge = 'success-subtle text-success'

        aggregated.append({
            'location_id': loc_id,
            'name': item['location__name'],
            'city': item['location__city'],
            'state': item['location__state'],
            'latitude': item['location__latitude'],
            'longitude': item['location__longitude'],
            'region_type': item['location__region_type'] or 'urban',
            'total_crimes': total,
            'critical_crimes': critical_cnt,
            'high_crimes': item['high_cnt'],
            'medium_crimes': item['med_cnt'],
            'low_crimes': item['low_cnt'],
            'top_category': top_cat,
            'categories_summary': categories_summary,
            'solved_crimes': solved_cnt,
            'solved_percentage': round((solved_cnt / total) * 100, 1) if total else 0,
            'risk_tier': risk_tier,
            'risk_badge': risk_badge,
        })

    return aggregated


def aggregate_by_city(queryset):
    """
    Groups crime records by city/district with incident counts and top categories.
    Uses conditional aggregation to eliminate N+1 queries.
    """
    city_groups = (
        queryset.values('location__city')
        .annotate(
            total_crimes=Count('id'),
            loc_count=Count('location', distinct=True),
            critical_crimes=Count('id', filter=Q(severity='critical')),
        )
        .order_by('-total_crimes')
    )

    # Top category per city in one single pass
    city_cats_qs = (
        queryset.values('location__city', 'category__name')
        .annotate(cnt=Count('id'))
        .order_by('location__city', '-cnt')
    )
    city_top_cat = {}
    for cc in city_cats_qs:
        c_name = cc['location__city']
        if c_name not in city_top_cat:
            city_top_cat[c_name] = cc['category__name']

    cities = []
    for item in city_groups:
        city_name = item['location__city'] or 'Unspecified City'
        cities.append({
            'city': city_name,
            'total_crimes': item['total_crimes'],
            'location_count': item['loc_count'],
            'critical_crimes': item['critical_crimes'],
            'top_category': city_top_cat.get(item['location__city'], 'N/A'),
        })

    return cities
