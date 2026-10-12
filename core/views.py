import logging
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from accounts.decorators import admin_required
from crime_data.models import CrimeRecord, CrimeCategory, Location
from prediction.models import PredictionResult
from .forms import ContactForm
from .models import AuditLog

logger = logging.getLogger(__name__)


def home_view(request):
    """
    Public landing page presenting platform statistics, features overview,
    and calls-to-action.
    """
    total_records = CrimeRecord.objects.count()
    total_categories = CrimeCategory.objects.count()
    total_locations = Location.objects.count()
    total_predictions = PredictionResult.objects.count()

    context = {
        'total_records': total_records,
        'total_categories': total_categories,
        'total_locations': total_locations,
        'total_predictions': total_predictions,
    }
    return render(request, 'core/home.html', context)


def about_view(request):
    """
    Information page describing system architecture, ontology graph,
    and machine learning forecasting methodology.
    """
    return render(request, 'core/about.html')


def contact_view(request):
    """
    Public contact form page. Validates input and saves ContactMessage instance.
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save()
            logger.info(f"Received contact message from {contact_msg.email}: {contact_msg.subject}")
            messages.success(request, "Thank you! Your message has been received. Our team will get back to you shortly.")
            return redirect('core:contact')
        else:
            messages.error(request, "Please verify all fields in the contact form.")
    else:
        form = ContactForm()

    return render(request, 'core/contact.html', {'form': form})


@login_required
def api_docs_view(request):
    """
    Interactive API Documentation view for developers and analysts.
    """
    return render(request, 'core/api_docs.html')


@login_required
@admin_required
def audit_log_view(request):
    """
    System activity audit log view restricted to administrators.
    Provides filtering by action, date range, search by username, and summary statistics.
    """
    logs = AuditLog.objects.select_related('user').all()

    action_filter = request.GET.get('action', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    search_query = request.GET.get('search', '').strip()

    if action_filter:
        logs = logs.filter(action=action_filter)

    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            logs = logs.filter(timestamp__date__gte=start_date.date())
        except ValueError:
            pass

    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
            logs = logs.filter(timestamp__date__lte=end_date.date())
        except ValueError:
            pass

    if search_query:
        logs = logs.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(resource_type__icontains=search_query) |
            Q(ip_address__icontains=search_query)
        )

    # Summary metrics for today
    today = timezone.localdate() if hasattr(timezone, 'localdate') else timezone.now().date()
    today_logs = AuditLog.objects.filter(timestamp__date=today)
    total_today = today_logs.count()
    unique_users_today = today_logs.exclude(user__isnull=True).values('user').distinct().count()

    most_common_stat = today_logs.values('action').annotate(count=Count('action')).order_by('-count').first()
    if most_common_stat:
        # Get readable label for action
        action_dict = dict(AuditLog.ACTION_CHOICES)
        most_common_action = action_dict.get(most_common_stat['action'], most_common_stat['action'])
    else:
        most_common_action = 'None'

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'action_choices': AuditLog.ACTION_CHOICES,
        'selected_action': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'total_today': total_today,
        'unique_users_today': unique_users_today,
        'most_common_action': most_common_action,
    }
    return render(request, 'core/audit_log.html', context)

