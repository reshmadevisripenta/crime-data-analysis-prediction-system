import logging
from django.db.models import Count
from crime_data.models import Location, CrimeRecord

logger = logging.getLogger(__name__)


def get_map_markers(queryset):
    """
    Transforms crime records / locations into marker data objects for Leaflet.js:
    [{'lat': float, 'lng': float, 'title': str, 'category': str, 'count': int, 'color': str}]
    """
    # Group by location and get crime count + primary category
    loc_stats = (
        queryset.values(
            'location_id',
            'location__name',
            'location__city',
            'location__latitude',
            'location__longitude'
        )
        .annotate(crime_count=Count('id'))
        .order_by('-crime_count')
    )

    markers = []
    for stat in loc_stats:
        lat = float(stat['location__latitude']) if stat['location__latitude'] else None
        lng = float(stat['location__longitude']) if stat['location__longitude'] else None
        if lat is None or lng is None:
            continue

        loc_id = stat['location_id']
        top_cat = (
            queryset.filter(location_id=loc_id)
            .values('category__name', 'category__color_code')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
            .first()
        )

        cat_name = top_cat['category__name'] if top_cat else 'General'
        color = top_cat['category__color_code'] if top_cat and top_cat.get('category__color_code') else '#1769FF'

        # Determine intensity color based on count
        count = stat['crime_count']
        if count >= 30:
            color = '#FF4560'  # High danger red
        elif count >= 15:
            color = '#FEB019'  # Warning orange
        else:
            color = '#00E396'  # Moderate green

        markers.append({
            'id': loc_id,
            'title': f"{stat['location__name']}, {stat['location__city']}",
            'lat': lat,
            'lng': lng,
            'count': count,
            'category': cat_name,
            'color': color,
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
    Groups crime records by location with breakdown by severity and resolution.
    """
    aggregated = []
    locations = (
        queryset.values('location__id', 'location__name', 'location__city')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    for item in locations:
        loc_id = item['location__id']
        loc_records = queryset.filter(location_id=loc_id)
        critical_cnt = loc_records.filter(severity='critical').count()
        solved_cnt = loc_records.filter(status__in=['solved', 'closed']).count()

        aggregated.append({
            'location_id': loc_id,
            'name': item['location__name'],
            'city': item['location__city'],
            'total_crimes': item['total'],
            'critical_crimes': critical_cnt,
            'solved_crimes': solved_cnt,
            'solved_percentage': round((solved_cnt / item['total']) * 100, 1) if item['total'] else 0
        })

    return aggregated
