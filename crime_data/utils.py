import logging
import pandas as pd
import numpy as np
from datetime import datetime
from django.utils import timezone
from .models import CrimeRecord, CrimeCategory, Location

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ['crime_category', 'incident_date', 'location']


def validate_dataset(df):
    """
    Validates that the uploaded DataFrame meets minimum structure requirements.
    Returns (is_valid: bool, errors_list: list).
    """
    errors = []
    
    # Normalize column names for flexible matching (lowercase, stripped, replace space with underscore)
    df_cols_normalized = {col.strip().lower().replace(' ', '_'): col for col in df.columns}
    
    missing_required = []
    for req in REQUIRED_COLUMNS:
        if req not in df_cols_normalized:
            missing_required.append(req)

    if missing_required:
        errors.append(f"Missing required column(s): {', '.join(missing_required)}. Found columns: {list(df.columns)}")

    if df.empty:
        errors.append("The uploaded dataset contains no rows of data.")

    is_valid = len(errors) == 0
    return is_valid, errors


def clean_dataset(df):
    """
    Cleans the uploaded DataFrame:
    - Normalizes column names
    - Strips whitespace
    - Drops completely duplicate rows
    - Standardizes date formats
    - Fills missing values with sensible defaults
    """
    df_cleaned = df.copy()

    # Standardize column names
    df_cleaned.columns = [col.strip().lower().replace(' ', '_') for col in df_cleaned.columns]

    # Drop total duplicate rows
    initial_rows = len(df_cleaned)
    df_cleaned.drop_duplicates(inplace=True)
    logger.info(f"Dropped {initial_rows - len(df_cleaned)} duplicate rows during cleaning.")

    # Fill missing values
    if 'description' in df_cleaned.columns:
        df_cleaned['description'] = df_cleaned['description'].fillna('Incident details not provided')
    else:
        df_cleaned['description'] = 'Incident details not provided'

    if 'severity' in df_cleaned.columns:
        df_cleaned['severity'] = df_cleaned['severity'].fillna('medium').astype(str).str.lower()
        # Ensure valid severity choice
        valid_severities = ['low', 'medium', 'high', 'critical']
        df_cleaned['severity'] = df_cleaned['severity'].apply(
            lambda s: s if s in valid_severities else 'medium'
        )
    else:
        df_cleaned['severity'] = 'medium'

    if 'status' in df_cleaned.columns:
        df_cleaned['status'] = df_cleaned['status'].fillna('reported').astype(str).str.lower().str.replace(' ', '_')
        valid_statuses = ['reported', 'under_investigation', 'solved', 'closed']
        df_cleaned['status'] = df_cleaned['status'].apply(
            lambda s: s if s in valid_statuses else 'reported'
        )
    else:
        df_cleaned['status'] = 'reported'

    # Convert date to standard ISO format
    if 'incident_date' in df_cleaned.columns:
        df_cleaned['incident_date'] = pd.to_datetime(df_cleaned['incident_date'], errors='coerce')

    return df_cleaned


def get_data_quality_stats(df):
    """
    Calculates summary quality statistics for a given DataFrame.
    Returns dict: {total, valid, invalid, missing_values, duplicates}
    """
    total = len(df)
    duplicates = int(df.duplicated().sum())

    missing_values = int(df.isnull().sum().sum())
    
    # Valid rows are those with non-null required columns
    normalized_cols = {col.strip().lower().replace(' ', '_'): col for col in df.columns}
    required_in_df = [normalized_cols[c] for c in REQUIRED_COLUMNS if c in normalized_cols]
    
    if len(required_in_df) == len(REQUIRED_COLUMNS):
        valid_rows_mask = df[required_in_df].notnull().all(axis=1)
        valid = int(valid_rows_mask.sum())
        invalid = total - valid
    else:
        valid = 0
        invalid = total

    return {
        'total': total,
        'valid': valid,
        'invalid': invalid,
        'missing_values': missing_values,
        'duplicates': duplicates,
    }


def process_dataset(upload_instance, df):
    """
    Processes the uploaded DataFrame and creates CrimeRecord instances.
    Updates the DatasetUpload status and record counts.
    """
    upload_instance.status = 'processing'
    upload_instance.save(update_fields=['status'])

    # Clean the dataset first
    cleaned_df = clean_dataset(df)
    total_rows = len(cleaned_df)
    valid_count = 0
    invalid_count = 0
    errors = []

    # Cache categories and locations for quick lookup
    categories = {c.name.lower(): c for c in CrimeCategory.objects.all()}
    locations = {l.name.lower(): l for l in Location.objects.all()}

    records_to_create = []

    for idx, row in cleaned_df.iterrows():
        try:
            cat_name = str(row.get('crime_category', '')).strip()
            loc_name = str(row.get('location', '')).strip()
            date_val = row.get('incident_date')

            if pd.isnull(date_val) or not cat_name or not loc_name:
                invalid_count += 1
                errors.append(f"Row {idx + 1}: Missing incident date, category, or location.")
                continue

            # Resolve Category
            category = categories.get(cat_name.lower())
            if not category:
                # Create category if not exists
                category = CrimeCategory.objects.create(
                    name=cat_name.title(),
                    description=f"Auto-generated category for {cat_name.title()}",
                    color_code='#1769FF'
                )
                categories[cat_name.lower()] = category

            # Resolve Location
            location = locations.get(loc_name.lower())
            if not location:
                # Determine lat/lng if available in row
                lat = row.get('latitude', 20.5937)
                lng = row.get('longitude', 78.9629)
                try:
                    lat = float(lat) if not pd.isnull(lat) else 20.5937
                    lng = float(lng) if not pd.isnull(lng) else 78.9629
                except (ValueError, TypeError):
                    lat = 20.5937
                    lng = 78.9629

                city_val = str(row.get('city', loc_name.title())).strip()
                state_val = str(row.get('state', 'State')).strip()

                location = Location.objects.create(
                    name=loc_name.title(),
                    city=city_val,
                    state=state_val,
                    latitude=lat,
                    longitude=lng,
                    region_type='urban'
                )
                locations[loc_name.lower()] = location

            # Parse time if provided
            incident_time = None
            raw_time = row.get('incident_time')
            if pd.notnull(raw_time):
                try:
                    if isinstance(raw_time, str):
                        incident_time = datetime.strptime(raw_time.strip(), '%H:%M:%S').time()
                    elif hasattr(raw_time, 'strftime'):
                        incident_time = raw_time
                except Exception:
                    incident_time = None

            incident_date = date_val.date() if hasattr(date_val, 'date') else pd.to_datetime(date_val).date()

            record = CrimeRecord(
                category=category,
                location=location,
                incident_date=incident_date,
                incident_time=incident_time,
                description=str(row.get('description', 'Incident details not provided'))[:500],
                severity=str(row.get('severity', 'medium')),
                status=str(row.get('status', 'reported')),
                source=str(row.get('source', upload_instance.original_filename))[:200],
                dataset_upload=upload_instance
            )
            records_to_create.append(record)
            valid_count += 1

            # Batch bulk create every 500 rows
            if len(records_to_create) >= 500:
                CrimeRecord.objects.bulk_create(records_to_create)
                records_to_create = []

        except Exception as e:
            invalid_count += 1
            errors.append(f"Row {idx + 1}: {str(e)}")
            logger.error(f"Error processing row {idx}: {e}")

    if records_to_create:
        CrimeRecord.objects.bulk_create(records_to_create)

    upload_instance.total_records = total_rows
    upload_instance.valid_records = valid_count
    upload_instance.invalid_records = invalid_count
    upload_instance.status = 'completed' if valid_count > 0 else 'failed'
    upload_instance.validation_errors = {'errors': errors[:50]}  # Store up to 50 sample errors
    upload_instance.processing_notes = f"Processed {total_rows} total rows. Successfully imported {valid_count} records. Failed rows: {invalid_count}."
    upload_instance.processed_at = timezone.now()
    upload_instance.save()

    logger.info(f"Dataset upload {upload_instance.id} processed: {valid_count} valid, {invalid_count} invalid.")
    return upload_instance
