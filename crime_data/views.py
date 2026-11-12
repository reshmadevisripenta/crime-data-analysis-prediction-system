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
from .utils import (
    validate_dataset,
    process_dataset,
    clean_dataset,
    get_data_quality_stats,
    detect_column_mapping,
    SCHEMA_TARGETS,
)

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
            ext = upload.original_filename.lower().split('.')[-1]
            if not upload.file_type:
                upload.file_type = 'excel' if ext in ['xlsx', 'xls'] else 'csv'
            upload.save()

            file_path = upload.file.path

            try:
                # Read into pandas DataFrame
                if ext in ['xlsx', 'xls']:
                    df = pd.read_excel(file_path)
                else:
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8')
                    except UnicodeDecodeError:
                        df = pd.read_csv(file_path, encoding='latin1')

                # Validate dataset structure and run smart column detection
                is_valid, errors, warnings, mapping_info, quality_stats = validate_dataset(df)
                missing_required = mapping_info.get('missing_required', [])
                ambiguities = mapping_info.get('ambiguities', [])

                if not is_valid and not mapping_info.get('target_to_original'):
                    # Completely empty or invalid file
                    upload.status = 'failed'
                    upload.validation_errors = {'errors': errors, 'warnings': warnings}
                    upload.save()
                    messages.error(request, f"Validation failed: {errors[0] if errors else 'Dataset is empty.'}")
                    return redirect('crime_data:upload_dataset')

                # AUTOMATIC INGESTION WORKFLOW:
                # If all required fields (category, location, incident date) are confidently detected
                # and no unresolved date ambiguities exist, immediately ingest the dataset!
                if not missing_required and not ambiguities:
                    process_dataset(upload, df)

                    Notification.create_notification(
                        user=request.user,
                        title="Dataset Ingestion Complete",
                        message=f"Dataset '{upload.original_filename}' processed: {upload.valid_records} valid records imported.",
                        notif_type="success",
                        category="upload",
                        action_url=f"/crime-data/preview/{upload.id}/"
                    )

                    if upload.invalid_records > 0:
                        messages.success(
                            request,
                            f"Dataset '{upload.original_filename}' successfully analyzed and ingested! "
                            f"{upload.valid_records} valid crime records were imported. "
                            f"({upload.invalid_records} incomplete row(s) were safely excluded)."
                        )
                    else:
                        messages.success(
                            request,
                            f"Dataset '{upload.original_filename}' successfully analyzed and ingested! "
                            f"All {upload.valid_records} records are clean and ready for analysis."
                        )
                    return redirect('crime_data:dataset_preview', pk=upload.pk)

                else:
                    # UNCERTAIN MAPPING WORKFLOW:
                    # Ask user only for the missing or ambiguous field(s) without technical jargon
                    upload.status = 'pending'
                    upload.validation_errors = {
                        'column_mapping': mapping_info.get('column_mappings', []),
                        'target_to_original': mapping_info.get('target_to_original', {}),
                        'original_to_target': mapping_info.get('original_to_target', {}),
                        'unmapped_columns': mapping_info.get('unmapped_columns', []),
                        'missing_required': missing_required,
                        'ambiguities': ambiguities,
                        'detected_fields_summary': mapping_info.get('detected_fields_summary', []),
                        'warnings': warnings,
                        'errors': errors,
                        'quality_score': 0,
                    }
                    upload.total_records = len(df)
                    upload.valid_records = 0
                    upload.invalid_records = len(df)
                    upload.save()

                    missing_names = [SCHEMA_TARGETS[m]['friendly_name'] for m in missing_required]
                    messages.warning(
                        request,
                        "Dataset analyzed! We found most fields, but need your quick confirmation on "
                        f"{' and '.join(missing_names) if missing_names else 'the incident date'} before ingesting."
                    )
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

    if request.user.is_admin() or request.user.is_analyst():
        recent_uploads = DatasetUpload.objects.all().order_by('-uploaded_at')[:10]
    else:
        recent_uploads = DatasetUpload.objects.filter(user=request.user).order_by('-uploaded_at')[:10]

    return render(request, 'crime_data/upload.html', {
        'form': form,
        'recent_uploads': recent_uploads,
        'upload_history': recent_uploads,
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

    # Build querystring preserving filters for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    filter_querystring = query_params.urlencode()

    categories = CrimeCategory.objects.all()
    locations = Location.objects.all()

    context = {
        'page_obj': page_obj,
        'records': page_obj,
        'categories': categories,
        'locations': locations,
        'selected_category': category_id,
        'selected_location': location_id,
        'selected_severity': severity,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'q': q,
        'filter_querystring': filter_querystring,
        'total_count': paginator.count,
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
    Shows preview of the first 100 records, friendly validation summary, quality statistics,
    and automatic field recognition audit for a DatasetUpload.
    """
    upload = get_object_or_404(DatasetUpload, pk=pk)
    records = CrimeRecord.objects.filter(dataset_upload=upload).select_related('category', 'location')[:100]

    val_data = upload.validation_errors or {}
    column_mappings = val_data.get('column_mapping', [])
    warnings = val_data.get('warnings', [])
    errors = val_data.get('errors', [])
    missing_required = val_data.get('missing_required', [])
    ambiguities = val_data.get('ambiguities', [])
    detected_fields_summary = val_data.get('detected_fields_summary', [])
    detected_date_format = val_data.get('detected_date_format', 'Standard Date')
    invalid_row_details = val_data.get('invalid_row_details', [])
    location_audit = val_data.get('location_audit', {})
    duplicates_removed = val_data.get('duplicates_removed', 0)
    missing_values = val_data.get('missing_values', 0)
    quality_score = val_data.get('quality_score')

    # If column mappings were not cached in validation_errors, compute on the fly from original file
    if not column_mappings and upload.file:
        try:
            file_path = upload.file.path
            ext = upload.original_filename.lower().split('.')[-1]
            if ext in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            else:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='latin1')
            mapping_result = detect_column_mapping(df)
            column_mappings = mapping_result['column_mappings']
            missing_required = mapping_result['missing_required']
            ambiguities = mapping_result.get('ambiguities', [])
            detected_fields_summary = mapping_result.get('detected_fields_summary', [])
        except Exception as e:
            logger.warning(f"Could not read original file for preview mapping: {e}")

    # Build available columns with sample values for clean dropdown selectors in manual confirmation
    available_columns_with_samples = []
    for col in column_mappings:
        orig = col['original_name']
        samples_list = col.get('sample_values', [])
        samples_text = ", ".join(samples_list[:2]) if samples_list else "no sample"
        available_columns_with_samples.append({
            'name': orig,
            'samples': samples_text,
            'target_field': col.get('target_field')
        })

    if quality_score is None:
        total = upload.total_records or 0
        valid = upload.valid_records or 0
        quality_score = round((valid / max(1, total)) * 100, 1) if total > 0 else 100.0

    stats = {
        'total': upload.total_records,
        'valid': upload.valid_records,
        'invalid': upload.invalid_records,
        'status': upload.status,
    }

    is_pending_mapping = (upload.status == 'pending') or bool(missing_required) or bool(ambiguities)

    # Build missing fields information with friendly names
    missing_fields_info = []
    for req in missing_required:
        if req in SCHEMA_TARGETS:
            missing_fields_info.append({
                'target': req,
                'friendly_name': SCHEMA_TARGETS[req]['friendly_name'],
                'description': SCHEMA_TARGETS[req]['description'],
            })

    return render(request, 'crime_data/preview.html', {
        'upload': upload,
        'dataset': upload,
        'records': records,
        'preview_rows': records,
        'stats': stats,
        'column_mappings': column_mappings,
        'schema_targets': SCHEMA_TARGETS,
        'detected_fields_summary': detected_fields_summary,
        'detected_date_format': detected_date_format,
        'invalid_row_details': invalid_row_details,
        'location_audit': location_audit,
        'available_columns_with_samples': available_columns_with_samples,
        'missing_fields_info': missing_fields_info,
        'ambiguities': ambiguities,
        'warnings': warnings,
        'errors': errors,
        'missing_required': missing_required,
        'duplicates_removed': duplicates_removed,
        'missing_values': missing_values,
        'quality_score': quality_score,
        'is_pending_mapping': is_pending_mapping,
    })


@login_required
@analyst_required
@require_POST
def remap_dataset_view(request, pk):
    """
    Accepts user-confirmed column mapping overrides, re-validates the dataset,
    and ingests records into CrimeRecord instances.
    """
    upload = get_object_or_404(DatasetUpload, pk=pk)
    file_path = upload.file.path
    ext = upload.original_filename.lower().split('.')[-1]

    try:
        if ext in ['xlsx', 'xls']:
            df = pd.read_excel(file_path)
        else:
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin1')

        # Collect mappings from form POST: supports both map_<target>=<col> and map_<col>=<target>
        custom_mapping = {}
        for key, value in request.POST.items():
            if key.startswith('map_') and value:
                identifier = key[4:]  # remove 'map_'
                if value != '__ignore__' and value != '__choose__':
                    if identifier in SCHEMA_TARGETS:
                        # e.g. map_incident_date = 'Date Reported'
                        custom_mapping[value] = identifier
                    elif value in SCHEMA_TARGETS:
                        # e.g. map_col_a = 'crime_category'
                        custom_mapping[identifier] = value
                    else:
                        custom_mapping[identifier] = value

        # Validate with the custom mapping
        is_valid, errors, warnings, mapping_info, quality_stats = validate_dataset(df, custom_mapping=custom_mapping)

        missing_required = mapping_info.get('missing_required', [])
        ambiguities = mapping_info.get('ambiguities', [])

        if missing_required:
            upload.status = 'pending'
            upload.validation_errors = {
                'column_mapping': mapping_info.get('column_mappings', []),
                'target_to_original': mapping_info.get('target_to_original', {}),
                'original_to_target': mapping_info.get('original_to_target', {}),
                'unmapped_columns': mapping_info.get('unmapped_columns', []),
                'missing_required': missing_required,
                'ambiguities': ambiguities,
                'warnings': warnings,
                'errors': errors,
            }
            upload.save()
            missing_names = [SCHEMA_TARGETS[m]['friendly_name'] for m in missing_required]
            messages.error(request, f"Please select columns for required field(s): {', '.join(missing_names)}.")
            return redirect('crime_data:dataset_preview', pk=upload.pk)

        # Clear existing records for this upload before re-processing
        CrimeRecord.objects.filter(dataset_upload=upload).delete()

        # Ingest with approved mapping
        process_dataset(upload, df, custom_mapping=custom_mapping)

        Notification.create_notification(
            user=request.user,
            title="Dataset Ingestion Complete",
            message=f"Dataset '{upload.original_filename}' successfully mapped and ingested: {upload.valid_records} records.",
            notif_type="success",
            category="upload",
            action_url=f"/crime-data/preview/{upload.id}/"
        )

        messages.success(
            request,
            f"Mapping confirmed! Successfully ingested {upload.valid_records} crime records from '{upload.original_filename}'."
        )
        return redirect('crime_data:dataset_preview', pk=upload.pk)

    except Exception as e:
        logger.error(f"Error remapping dataset {upload.id}: {e}", exc_info=True)
        messages.error(request, f"Failed to ingest dataset: {str(e)}")
        return redirect('crime_data:dataset_preview', pk=upload.pk)


def download_template_view(request):
    """
    Streams a standardized CSV template for dataset upload with schema headers and sample rows.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="crime_dataset_template.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'crime_category', 'location', 'city', 'state', 'latitude', 'longitude',
        'incident_date', 'incident_time', 'severity', 'status', 'description', 'source'
    ])
    writer.writerow([
        'Robbery', 'Main Road Commercial Zone', 'Rajahmundry', 'Andhra Pradesh', '17.0005', '81.8040',
        '2024-05-15', '14:30:00', 'high', 'under_investigation', 'Reported theft of mobile device near junction', 'City Police Dept'
    ])
    writer.writerow([
        'Burglary', 'Gandhinagar Market', 'Vijayawada', 'Andhra Pradesh', '16.5062', '80.6480',
        '2024-05-16', '02:15:00', 'medium', 'reported', 'Break-in at commercial store warehouse', 'District HQ'
    ])
    writer.writerow([
        'Assault', 'Beach Road Promenade', 'Visakhapatnam', 'Andhra Pradesh', '17.6868', '83.2185',
        '2024-05-17', '21:45:00', 'critical', 'solved', 'Physical altercation resolved on scene', 'Coastal Patrol'
    ])
    writer.writerow([
        'Theft', 'Central Railway Station', 'Tirupati', 'Andhra Pradesh', '13.6288', '79.4192',
        '2024-05-18', '09:10:00', 'low', 'closed', 'Bicycle stolen from transit parking zone', 'Railway Police'
    ])

    return response


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
