import logging
import io
import csv
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q

from accounts.decorators import admin_required, analyst_required
from notifications.models import Notification
from .models import CrimeRecord, DatasetUpload, CrimeCategory, Location
from .forms import DatasetUploadForm, CrimeRecordForm
from .utils import validate_dataset, process_dataset, clean_dataset, get_data_quality_stats

logger = logging.getLogger(__name__)


@analyst_required
def dataset_upload_view(request):
    """
    Handles CSV and Excel dataset uploads. Validates structure with pandas,
    processes rows asynchronously/synchronously into CrimeRecord objects,
    and creates notifications for the user.
    """
    if request.method == 'POST':
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.user = request.user
            upload.original_filename = request.FILES['file'].name
            upload.save()

            file_path = upload.file.path
            ext = upload.original_filename.lower().split('.')[-1]

            try:
                # Read into pandas DataFrame
                if ext in ['xlsx', 'xls']:
                    df = pd.read_excel(file_path)
                else:
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8')
                    except UnicodeDecodeError:
                        df = pd.read_csv(file_path, encoding='latin1')

                # Validate dataset structure
                is_valid, errors = validate_dataset(df)
                if not is_valid:
                    upload.status = 'failed'
                    upload.validation_errors = {'errors': errors}
                    upload.save()
                    messages.error(request, f"Validation failed: {errors[0]}")
                    return redirect('crime_data:upload_dataset')

                # Process dataset and create records
                process_dataset(upload, df)

                # Send success notification
                Notification.create_notification(
                    user=request.user,
                    title="Dataset Upload Processed",
                    message=f"Dataset '{upload.original_filename}' processed: {upload.valid_records} records imported successfully.",
                    notif_type="success",
                    category="upload",
                    action_url=f"/crime-data/preview/{upload.id}/"
                )

                messages.success(request, f"Successfully uploaded and processed '{upload.original_filename}'. {upload.valid_records} records imported.")
                return redirect('crime_data:dataset_preview', pk=upload.pk)

            except Exception as e:
                logger.error(f"Error processing dataset {upload.id}: {str(e)}", exc_info=True)
                upload.status = 'failed'
                upload.processing_notes = str(e)
                upload.save()
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect('crime_data:upload_dataset')
        else:
            messages.error(request, "Invalid upload form. Please check the file format and size.")
    else:
        form = DatasetUploadForm()

    recent_uploads = DatasetUpload.objects.filter(user=request.user).order_by('-uploaded_at')[:10]
    return render(request, 'crime_data/upload.html', {
        'form': form,
        'recent_uploads': recent_uploads
    })


@login_required
def crime_record_list_view(request):
    """
    Searchable, filterable, and paginated list of all CrimeRecords.
    Filters: search query (q), category, location, severity, status, date_from, date_to.
    """
    queryset = CrimeRecord.objects.select_related('category', 'location', 'dataset_upload').all()

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(description__icontains=q) |
            Q(category__name__icontains=q) |
            Q(location__name__icontains=q) |
            Q(location__city__icontains=q) |
            Q(source__icontains=q)
        )

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # Location filter
    location_id = request.GET.get('location')
    if location_id:
        queryset = queryset.filter(location_id=location_id)

    # Severity filter
    severity = request.GET.get('severity')
    if severity:
        queryset = queryset.filter(severity=severity)

    # Status filter
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)

    # Date range filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        queryset = queryset.filter(incident_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(incident_date__lte=date_to)

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = CrimeCategory.objects.all()
    locations = Location.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'locations': locations,
        'selected_category': category_id,
        'selected_location': location_id,
        'selected_severity': severity,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'q': q,
        'total_count': queryset.count(),
    }
    return render(request, 'crime_data/list.html', context)


@login_required
def crime_record_detail_view(request, pk):
    """Displays detailed information for a single CrimeRecord."""
    record = get_object_or_404(CrimeRecord.objects.select_related('category', 'location', 'dataset_upload'), pk=pk)
    return render(request, 'crime_data/detail.html', {'record': record})


@login_required
@analyst_required
def crime_record_create_view(request):
    """Creates a new CrimeRecord manually."""
    if request.method == 'POST':
        form = CrimeRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, f"Crime record #{record.id} created successfully.")
            return redirect('crime_data:record_detail', pk=record.pk)
        else:
            messages.error(request, "Failed to create crime record. Please check the inputs.")
    else:
        form = CrimeRecordForm()

    return render(request, 'crime_data/add_edit.html', {
        'form': form,
        'action': 'Create'
    })


@login_required
@analyst_required
def crime_record_update_view(request, pk):
    """Updates an existing CrimeRecord."""
    record = get_object_or_404(CrimeRecord, pk=pk)
    if request.method == 'POST':
        form = CrimeRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, f"Crime record #{record.id} updated successfully.")
            return redirect('crime_data:record_detail', pk=record.pk)
        else:
            messages.error(request, "Please fix errors in the form.")
    else:
        form = CrimeRecordForm(instance=record)

    return render(request, 'crime_data/add_edit.html', {
        'form': form,
        'record': record,
        'action': 'Edit'
    })


@admin_required
@require_POST
def crime_record_delete_view(request, pk):
    """Deletes a CrimeRecord (Admin only, POST request only)."""
    record = get_object_or_404(CrimeRecord, pk=pk)
    record_id = record.id
    record.delete()
    messages.success(request, f"Crime record #{record_id} has been deleted.")
    return redirect('crime_data:record_list')


@login_required
def dataset_preview_view(request, pk):
    """
    Shows preview of the first 100 records and quality statistics
    for a DatasetUpload.
    """
    upload = get_object_or_404(DatasetUpload, pk=pk)
    records = CrimeRecord.objects.filter(dataset_upload=upload).select_related('category', 'location')[:100]

    stats = {
        'total': upload.total_records,
        'valid': upload.valid_records,
        'invalid': upload.invalid_records,
        'status': upload.status,
    }

    return render(request, 'crime_data/preview.html', {
        'upload': upload,
        'records': records,
        'stats': stats,
    })


@login_required
def download_cleaned_dataset_view(request, pk):
    """
    Streams cleaned dataset as a CSV download for a given DatasetUpload.
    """
    upload = get_object_or_404(DatasetUpload, pk=pk)
    records = CrimeRecord.objects.filter(dataset_upload=upload).select_related('category', 'location')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cleaned_{upload.original_filename}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Crime Category', 'Location', 'City', 'State',
        'Latitude', 'Longitude', 'Incident Date', 'Incident Time',
        'Severity', 'Status', 'Description', 'Source'
    ])

    for r in records:
        writer.writerow([
            r.id,
            r.category.name,
            r.location.name,
            r.location.city,
            r.location.state,
            r.location.latitude,
            r.location.longitude,
            r.incident_date,
            r.incident_time or '',
            r.severity,
            r.status,
            r.description,
            r.source
        ])

    return response


@admin_required
@require_POST
def delete_dataset_view(request, pk):
    """Deletes a DatasetUpload and cascades/removes associated records."""
    upload = get_object_or_404(DatasetUpload, pk=pk)
    name = upload.original_filename
    # Delete associated records
    CrimeRecord.objects.filter(dataset_upload=upload).delete()
    upload.delete()
    messages.success(request, f"Dataset '{name}' and associated records have been deleted.")
    return redirect('crime_data:upload_dataset')
