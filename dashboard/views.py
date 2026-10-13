import logging
import json
from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from crime_data.models import CrimeRecord, CrimeCategory, Location, DatasetUpload
from prediction.models import PredictionResult
from model_training.models import MLModel
from notifications.models import Notification

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    """
    Main dashboard view.
    Gathers key system metrics, recent activity, crime trend line data,
    category distribution for charts, and unread notifications.
    """
    now = timezone.now()
    
    # 1. Metric Counts
    total_crime_records = CrimeRecord.objects.count()
    total_categories = CrimeCategory.objects.count()
    total_locations = Location.objects.count()
    total_predictions = PredictionResult.objects.count()

    # 2. Recent uploads (last 5)
    recent_uploads = DatasetUpload.objects.select_related('user').order_by('-uploaded_at')[:5]

    # 3. Latest predictions (last 5)
    latest_predictions = PredictionResult.objects.select_related(
        'model', 'location', 'category', 'requested_by'
    ).order_by('-prediction_date', '-id')[:5]

    # 4. Recent notifications (last 10)
    recent_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]

    # 5. Crime trends for the last 12 months
    # Generate labels for past 12 months
    trend_labels = []
    trend_data = []
    start_date = (now - relativedelta(months=11)).replace(day=1)
    
    for i in range(12):
        month_dt = start_date + relativedelta(months=i)
        label_str = month_dt.strftime('%b %Y')
        trend_labels.append(label_str)
        
        # Count records in that month
        m_start = month_dt.date()
        if month_dt.month == 12:
            m_end = datetime(month_dt.year + 1, 1, 1).date()
        else:
            m_end = datetime(month_dt.year, month_dt.month + 1, 1).date()

        cnt = CrimeRecord.objects.filter(
            incident_date__gte=m_start,
            incident_date__lt=m_end
        ).count()
        trend_data.append(cnt)

    # 6. Category distribution data (for doughnut chart)
    category_counts = (
        CrimeCategory.objects.annotate(crime_count=Count('crime_records'))
        .order_by('-crime_count')
    )
    category_labels = [c.name for c in category_counts]
    category_values = [c.crime_count for c in category_counts]
    category_colors = [c.color_code or '#1769FF' for c in category_counts]

    # Fallback colors if empty
    if not category_labels:
        category_labels = ["No Data"]
        category_values = [0]
        category_colors = ["#CED4DA"]

    # 7. Severity breakdown
    severity_counts = dict(
        CrimeRecord.objects.values('severity')
        .annotate(total=Count('id'))
        .values_list('severity', 'total')
    )

    # 8. Latest trained model evaluation (if available)
    latest_model = MLModel.objects.filter(status='trained').prefetch_related('evaluations').order_by('-created_at').first()
    latest_eval = latest_model.evaluations.first() if latest_model else None

    context = {
        'total_records': total_crime_records,
        'total_crime_records': total_crime_records,
        'total_categories': total_categories,
        'total_locations': total_locations,
        'total_predictions': total_predictions,
        'latest_eval': latest_eval,
        'recent_uploads': recent_uploads,
        'latest_predictions': latest_predictions,
        'recent_notifications': recent_notifications,
        # Chart JSON data
        'trend_labels_json': json.dumps(trend_labels),
        'trend_data_json': json.dumps(trend_data),
        'category_labels_json': json.dumps(category_labels),
        'category_values_json': json.dumps(category_values),
        'category_colors_json': json.dumps(category_colors),
        'severity_counts': severity_counts,
    }

    return render(request, 'dashboard/dashboard.html', context)
