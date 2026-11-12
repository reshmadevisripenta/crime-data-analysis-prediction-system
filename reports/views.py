import os
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from accounts.decorators import analyst_required, admin_required
from crime_data.models import Location, CrimeCategory
from notifications.models import Notification
from .models import Report, ReportExport
from .utils import get_report_data, generate_pdf_report, generate_csv_report

logger = logging.getLogger(__name__)


@login_required
def reports_view(request):
    """
    Renders reports dashboard:
    - Report configuration form (type, location, category, date range)
    - History of previously generated reports
    """
    reports_history = Report.objects.select_related('location', 'category', 'generated_by').prefetch_related('exports').order_by('-created_at')
    locations = Location.objects.all()
    categories = CrimeCategory.objects.all()

    context = {
        'reports_history': reports_history,
        'report_types': Report.REPORT_TYPE_CHOICES,
        'locations': locations,
        'categories': categories,
        'selected_location': str(request.GET.get('location_id', request.GET.get('location', ''))),
        'selected_category': str(request.GET.get('category_id', request.GET.get('category', ''))),
        'selected_location_id': str(request.GET.get('location_id', request.GET.get('location', ''))),
        'selected_category_id': str(request.GET.get('category_id', request.GET.get('category', ''))),
        'date_from': request.GET.get('date_from', ''),
        'date_to': request.GET.get('date_to', ''),
    }
    return render(request, 'reports/reports.html', context)


@analyst_required
@require_POST
def generate_report_view(request):
    """
    Generates a new Report and builds PDF / CSV exports.
    Notifies user when ready.
    """
    raw_name = request.POST.get('name', '').strip()
    report_type = request.POST.get('report_type', 'crime_analysis')
    description = request.POST.get('description', '').strip()
    date_from = request.POST.get('date_from') or None
    date_to = request.POST.get('date_to') or None
    location_id = request.POST.get('location_id') or request.POST.get('location') or None
    category_id = request.POST.get('category_id') or request.POST.get('category') or None

    location = Location.objects.filter(pk=int(location_id)).first() if (location_id and str(location_id).isdigit()) else None
    category = CrimeCategory.objects.filter(pk=int(category_id)).first() if (category_id and str(category_id).isdigit()) else None

    if not raw_name:
        type_lbl = dict(Report.REPORT_TYPE_CHOICES).get(report_type, 'Crime Analysis')
        loc_lbl = f" ({location.name})" if location else ""
        name = f"{type_lbl}{loc_lbl} - {timezone.now().strftime('%b %d, %Y')}"
    else:
        name = raw_name

    report = Report.objects.create(
        name=name,
        report_type=report_type,
        description=description,
        date_from=date_from,
        date_to=date_to,
        location=location,
        category=category,
        generated_by=request.user,
        status='generating'
    )

    try:
        report_data = get_report_data(report)

        # Generate PDF export
        pdf_rel_path = generate_pdf_report(report, report_data)
        pdf_full_path = os.path.join(settings.MEDIA_ROOT, pdf_rel_path)
        pdf_size = os.path.getsize(pdf_full_path) if os.path.exists(pdf_full_path) else 0

        ReportExport.objects.create(
            report=report,
            export_format='pdf',
            file=pdf_rel_path,
            file_size=pdf_size
        )

        # Generate CSV export
        csv_rel_path = generate_csv_report(report, report_data)
        csv_full_path = os.path.join(settings.MEDIA_ROOT, csv_rel_path)
        csv_size = os.path.getsize(csv_full_path) if os.path.exists(csv_full_path) else 0

        ReportExport.objects.create(
            report=report,
            export_format='csv',
            file=csv_rel_path,
            file_size=csv_size
        )

        report.status = 'ready'
        report.save(update_fields=['status'])

        # Notify user
        Notification.create_notification(
            user=request.user,
            title="Report Ready for Download",
            message=f"Report '{report.name}' has been compiled successfully ({report_data['total_crimes']} records).",
            notif_type="success",
            category="report",
            action_url="/reports/"
        )

        messages.success(request, f"Report '{report.name}' generated successfully.")
    except Exception as e:
        logger.error(f"Error generating report {report.id}: {e}", exc_info=True)
        report.status = 'failed'
        report.save(update_fields=['status'])
        messages.error(request, f"Failed to generate report: {str(e)}")

    return redirect('reports:reports')


@login_required
def download_report_view(request, export_id):
    """
    Streams the requested ReportExport file (PDF or CSV) to the browser.
    """
    export = get_object_or_404(ReportExport, pk=export_id)
    if not export.file or not os.path.exists(export.file.path):
        raise Http404("Report file does not exist on disk.")

    with open(export.file.path, 'rb') as f:
        file_data = f.read()

    content_type = 'application/pdf' if export.export_format == 'pdf' else 'text/csv'
    ext = export.export_format
    filename = f"{export.report.name.replace(' ', '_')}_{export.id}.{ext}"

    response = HttpResponse(file_data, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@admin_required
@require_POST
def delete_report_view(request, pk):
    """
    Deletes a Report and its generated export files on disk (Admin only).
    """
    report = get_object_or_404(Report, pk=pk)
    name = report.name

    for export in report.exports.all():
        if export.file and os.path.exists(export.file.path):
            try:
                os.remove(export.file.path)
            except OSError:
                pass

    report.delete()
    messages.success(request, f"Report '{name}' deleted successfully.")
    return redirect('reports:reports')
