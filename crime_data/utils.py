import logging
import re
import pandas as pd
import numpy as np
from datetime import datetime, date
from django.utils import timezone
from .models import CrimeRecord, CrimeCategory, Location

logger = logging.getLogger(__name__)

# System Schema Targets Definition with Friendly Labels & Extensive Aliases
SCHEMA_TARGETS = {
    'crime_category': {
        'label': 'Crime Category / Offense',
        'friendly_name': 'Crime Offense / Category',
        'required': True,
        'description': 'Primary crime type or legal classification of the incident.',
        'aliases': [
            'crime_type', 'crime_description', 'offense', 'crime', 'category', 'crime_name',
            'crime_category', 'type_of_crime', 'offense_type', 'offense_description',
            'crime_offense', 'primary_type', 'charge', 'charge_description', 'crime_code_description',
            'incident_category', 'incident_type', 'law_offense', 'offense_category',
            'crime_classification', 'incident_offense', 'offence', 'offence_type',
            'offence_description', 'primary_offense', 'statute_description'
        ]
    },
    'location': {
        'label': 'Location / Neighborhood',
        'friendly_name': 'Location / Area',
        'required': True,
        'description': 'City, location, area, neighborhood, district, or place of occurrence.',
        'aliases': [
            'city', 'location', 'area', 'district', 'neighborhood', 'jurisdiction', 'place',
            'location_name', 'neighbourhood', 'block', 'address', 'street_address',
            'premises', 'beat', 'sector', 'precinct', 'ward', 'town', 'zone',
            'location_description', 'place_of_occurrence', 'incident_location',
            'scene', 'police_beat', 'subdivision'
        ]
    },
    'incident_date': {
        'label': 'Incident Date (Occurrence)',
        'friendly_name': 'Incident Date',
        'required': True,
        'description': 'Date the crime incident actually occurred (Date of Occurrence).',
        'aliases': [
            'date_of_occurrence', 'crime_date', 'incident_date', 'occurrence_date',
            'date_occurred', 'occurred_date', 'event_date', 'incident_datetime',
            'date', 'datetime', 'timestamp', 'incident_day'
        ]
    },
    'incident_time': {
        'label': 'Incident Time',
        'friendly_name': 'Incident Time',
        'required': False,
        'description': 'Time the crime occurred (Time of Occurrence).',
        'aliases': [
            'time_of_occurrence', 'crime_time', 'incident_time', 'time',
            'time_occurred', 'occurred_time', 'incident_hour', 'hour',
            'time_reported', 'dispatch_time'
        ]
    },
    'crime_code': {
        'label': 'Crime Code',
        'friendly_name': 'Crime / Penal Code',
        'required': False,
        'description': 'Numeric or alphanumeric crime/penal offense code.',
        'aliases': [
            'crime_code', 'offense_code', 'charge_code', 'incident_code', 'statute_code',
            'section', 'ipc_section', 'penal_code', 'code', 'crime_id'
        ]
    },
    'victim_age': {
        'label': 'Victim Age',
        'friendly_name': 'Victim Age',
        'required': False,
        'description': 'Age of the victim at the time of the incident.',
        'aliases': [
            'victim_age', 'age', 'age_of_victim', 'victim_s_age', 'vic_age'
        ]
    },
    'victim_gender': {
        'label': 'Victim Gender',
        'friendly_name': 'Victim Gender',
        'required': False,
        'description': 'Gender or sex of the victim.',
        'aliases': [
            'victim_gender', 'victim_sex', 'gender', 'sex', 'victim_s_gender', 'vic_sex', 'vic_gender'
        ]
    },
    'weapon_used': {
        'label': 'Weapon Used',
        'friendly_name': 'Weapon Used',
        'required': False,
        'description': 'Type of weapon or weapon used during the incident.',
        'aliases': [
            'weapon_used', 'weapon', 'weapon_type', 'weapon_description', 'weapon_desc',
            'arms', 'arms_used'
        ]
    },
    'severity': {
        'label': 'Incident Severity',
        'friendly_name': 'Severity Level',
        'required': False,
        'description': 'Severity tier: low, medium, high, critical.',
        'aliases': [
            'severity', 'crime_severity', 'severity_level', 'priority', 'degree',
            'level', 'incident_severity', 'risk_level', 'threat_level'
        ]
    },
    'status': {
        'label': 'Investigation Status',
        'friendly_name': 'Status / Disposition',
        'required': False,
        'description': 'Status: reported, under_investigation, solved, closed.',
        'aliases': [
            'status', 'investigation_status', 'case_status', 'resolution_status',
            'disposition', 'resolution', 'incident_status', 'outcome',
            'arrest_status', 'clearance_status', 'record_status'
        ]
    },
    'description': {
        'label': 'Incident Description',
        'friendly_name': 'Description / Narrative',
        'required': False,
        'description': 'Narrative notes, summary, remarks, or modus operandi.',
        'aliases': [
            'description', 'incident_description', 'narrative', 'details',
            'summary', 'remarks', 'notes', 'incident_details', 'crime_details',
            'modus_operandi', 'mo', 'statement'
        ]
    },
    'city': {
        'label': 'City / Municipality',
        'friendly_name': 'City',
        'required': False,
        'description': 'City or municipality jurisdiction.',
        'aliases': [
            'city', 'municipality', 'town', 'metro', 'urban_center', 'city_name'
        ]
    },
    'state': {
        'label': 'State / Province',
        'friendly_name': 'State',
        'required': False,
        'description': 'State or provincial jurisdiction.',
        'aliases': [
            'state', 'province', 'region', 'state_name'
        ]
    },
    'latitude': {
        'label': 'GPS Latitude',
        'friendly_name': 'Latitude',
        'required': False,
        'description': 'GPS Latitude coordinate (-90 to +90).',
        'aliases': [
            'latitude', 'lat', 'gps_latitude', 'y', 'y_coord', 'y_coordinate',
            'geo_latitude', 'lat_coord', 'gps_lat'
        ]
    },
    'longitude': {
        'label': 'GPS Longitude',
        'friendly_name': 'Longitude',
        'required': False,
        'description': 'GPS Longitude coordinate (-180 to +180).',
        'aliases': [
            'longitude', 'lng', 'lon', 'gps_longitude', 'x', 'x_coord', 'x_coordinate',
            'geo_longitude', 'lon_coord', 'long', 'gps_lon', 'gps_lng'
        ]
    },
    'source': {
        'label': 'Reporting Agency / Source',
        'friendly_name': 'Data Source',
        'required': False,
        'description': 'Police department, branch, or reporting agency.',
        'aliases': [
            'source', 'agency', 'department', 'police_station', 'reporting_station',
            'reporting_agency', 'data_source', 'data_origin', 'police_dept', 'police_branch'
        ]
    },
    'report_date': {
        'label': 'Date Reported',
        'friendly_name': 'Date Reported (Filing Date)',
        'required': False,
        'description': 'Date the incident was formally reported to authorities.',
        'aliases': [
            'date_reported', 'reported_date', 'report_date', 'date_of_report',
            'filing_date', 'complaint_date', 'lodged_date', 'registration_date'
        ]
    }
}

REQUIRED_COLUMNS = ['crime_category', 'incident_date', 'location']

# Verified Regional Geographic Centroids for Reliable Approximate Positioning
# (Used only when exact GPS coordinates are not provided in dataset rows)
KNOWN_COORDINATES = {
    'rajahmundry': (17.0005, 81.8040),
    'east godavari': (17.0005, 81.8040),
    'vijayawada': (16.5062, 80.6480),
    'ntr': (16.5062, 80.6480),
    'visakhapatnam': (17.6868, 83.2185),
    'vizag': (17.6868, 83.2185),
    'guntur': (16.3067, 80.4365),
    'tirupati': (13.6288, 79.4192),
    'kurnool': (15.8281, 78.0373),
    'kakinada': (16.9891, 82.2475),
    'nellore': (14.4426, 79.9865),
    'kadapa': (14.4673, 78.8242),
    'anantapur': (14.6819, 77.6006),
    'eluru': (16.7107, 81.0952),
    'ongole': (15.5057, 80.0499),
    'chittoor': (13.2172, 79.1003),
    'srikakulam': (18.2969, 83.8967),
    'vizianagaram': (18.1067, 83.3956),
    'hyderabad': (17.3850, 78.4867),
    'secunderabad': (17.4399, 78.4983),
    'cyberabad': (17.4401, 78.3489),
    'warangal': (17.9689, 79.5941),
    'bengaluru': (12.9716, 77.5946),
    'bangalore': (12.9716, 77.5946),
    'mysuru': (12.2958, 76.6394),
    'chennai': (13.0827, 80.2707),
    'coimbatore': (11.0168, 76.9558),
    'mumbai': (19.0760, 72.8777),
    'pune': (18.5204, 73.8567),
    'nagpur': (21.1458, 79.0882),
    'delhi': (28.6139, 77.2090),
    'new delhi': (28.6139, 77.2090),
    'kolkata': (22.5726, 88.3639),
    'ahmedabad': (23.0225, 72.5714),
    'surat': (21.1702, 72.8311),
    'jaipur': (26.9124, 75.7873),
    'lucknow': (26.8467, 80.9462),
    'kanpur': (26.4499, 80.3319),
    'bhopal': (23.2599, 77.4126),
    'indore': (22.7196, 75.8577),
    'patna': (25.5941, 85.1376),
    'chandigarh': (30.7333, 76.7794),
    'kochi': (9.9312, 76.2673),
    'thiruvananthapuram': (8.5241, 76.9366),
}


def normalize_header(header_name):
    """
    Normalizes a column header string:
    Strips whitespace, converts to lowercase, replaces punctuation and spaces with underscores.
    """
    if not isinstance(header_name, str):
        header_name = str(header_name)
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '_', header_name.strip().lower())
    return cleaned.strip('_')


def parse_date_value(val, dayfirst=True):
    """
    Intelligently parses a single date value into a datetime.date object.
    Supports:
    - Native datetime.date and datetime.datetime
    - Excel serial numbers (int / float e.g. 45427 -> 2024-05-15)
    - ISO strings: YYYY-MM-DD, YYYY/MM/DD, YYYY-MM-DD HH:MM:SS, ISO8601
    - Formatted strings: DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, DD.MM.YYYY
    """
    if val is None or pd.isnull(val):
        return None
    if isinstance(val, (datetime, date)):
        if hasattr(val, 'date'):
            return val.date()
        return val

    # Excel numeric date check (integers or floats between 25000 and 65000)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        try:
            if 25000 <= float(val) <= 65000:
                dt = pd.to_datetime(val, unit='D', origin='1899-12-30')
                return dt.date()
        except Exception:
            pass

    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'nat', 'none', 'null', 'n/a', '-', 'nil', '']:
        return None

    # Check if string is a numeric string (e.g. '45427')
    if val_str.replace('.', '', 1).isdigit() and len(val_str) in [4, 5]:
        try:
            num = float(val_str)
            if 25000 <= num <= 65000:
                dt = pd.to_datetime(num, unit='D', origin='1899-12-30')
                return dt.date()
        except Exception:
            pass

    # Try standard string date parsing with dayfirst heuristic
    try:
        dt = pd.to_datetime(val_str, dayfirst=dayfirst, errors='coerce')
        if pd.notnull(dt):
            d = dt.date()
            if 1900 <= d.year <= 2100:
                return d
    except Exception:
        pass

    # Fallback to direct strptime for tricky cases
    for fmt in [
        '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d',
        '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M:%S', '%d-%b-%Y', '%d-%B-%Y', '%Y%m%d'
    ]:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.date()
        except ValueError:
            pass

    return None


def parse_date_series(series):
    """
    Intelligently parses dates across a pandas Series.
    Detects whether format is DD/MM/YYYY or MM/DD/YYYY across the series:
    - If any value has first token > 12, then it must be DD/MM/YYYY (dayfirst=True).
    - If any value has second token > 12, then it must be MM/DD/YYYY (dayfirst=False).
    - If ambiguous across all rows (all numbers <= 12), defaults to dayfirst=True
      (standard in India and international) and notes potential ambiguity.

    Returns:
    (parsed_dates: list of datetime.date or None,
     invalid_indices: list of 1-based row numbers,
     invalid_explanations: list of dicts,
     detected_format: str,
     is_ambiguous: bool)
    """
    has_first_gt_12 = False
    has_second_gt_12 = False
    has_iso = False
    has_excel_num = False

    sample_strings = []
    for val in series.dropna().head(100):
        if isinstance(val, (int, float)) and not isinstance(val, bool) and 25000 <= float(val) <= 65000:
            has_excel_num = True
            continue
        v_str = str(val).strip()
        if not v_str or v_str.lower() in ['nan', 'none', 'null', 'n/a']:
            continue
        sample_strings.append(v_str)

        # Check ISO YYYY-MM-DD or YYYY/MM/DD
        if re.match(r'^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}', v_str):
            has_iso = True
            continue

        # Check XX/YY/ZZZZ or XX-YY-ZZZZ
        m = re.match(r'^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', v_str)
        if m:
            p1, p2 = int(m.group(1)), int(m.group(2))
            if p1 > 12 >= p2:
                has_first_gt_12 = True
            elif p2 > 12 >= p1:
                has_second_gt_12 = True

    if has_excel_num and not sample_strings:
        detected_format = 'Excel Serial Date'
        dayfirst = True
        is_ambiguous = False
    elif has_iso and not (has_first_gt_12 or has_second_gt_12):
        detected_format = 'YYYY-MM-DD (ISO)'
        dayfirst = False
        is_ambiguous = False
    elif has_first_gt_12 and not has_second_gt_12:
        detected_format = 'DD/MM/YYYY (Day-First)'
        dayfirst = True
        is_ambiguous = False
    elif has_second_gt_12 and not has_first_gt_12:
        detected_format = 'MM/DD/YYYY (Month-First)'
        dayfirst = False
        is_ambiguous = False
    else:
        detected_format = 'DD/MM/YYYY (Standard)'
        dayfirst = True
        is_ambiguous = bool(sample_strings and not has_iso)

    parsed_dates = []
    invalid_indices = []
    invalid_explanations = []

    for idx, val in enumerate(series):
        row_num = idx + 1
        d = parse_date_value(val, dayfirst=dayfirst)
        parsed_dates.append(d)
        if d is None:
            invalid_indices.append(row_num)
            raw_display = str(val).strip() if (val is not None and not pd.isnull(val)) else "(Empty)"
            invalid_explanations.append({
                'row': row_num,
                'field': 'Incident Date',
                'issue': f'Invalid Date: "{raw_display}" could not be recognized as a valid calendar date.'
            })

    return parsed_dates, invalid_indices, invalid_explanations, detected_format, is_ambiguous


def detect_column_mapping(df, manual_mapping=None):
    """
    Automatically detects column meanings from DataFrame headers and sample values.
    Maps recognized columns to internal schema targets:
    - Prefers Date of Occurrence over Date Reported for incident_date
    - Accurately identifies Crime Category, Location, Time, and optional fields
    - Strictly avoids false positives for unrelated columns
    - Flags ambiguities (e.g. if only Date Reported is provided) for user confirmation
    """
    manual_mapping = manual_mapping or {}

    target_to_original = {}
    original_to_target = {}
    column_mappings = []
    unmapped_columns = []
    ambiguities = []
    friendly_notes = []

    # Priority order for mapping schema targets
    priority_order = [
        'incident_date',   # Occurrence date prioritized first
        'crime_category',
        'location',
        'city',
        'incident_time',
        'report_date',     # Filing date
        'severity',
        'status',
        'weapon_used',
        'victim_age',
        'victim_gender',
        'crime_code',
        'latitude',
        'longitude',
        'state',
        'description',
        'source'
    ]

    # Pre-compute normalized names and sample values
    df_cols_info = []
    for col in df.columns:
        col_str = str(col).strip()
        norm_col = normalize_header(col_str)

        samples = []
        if col in df:
            non_null_series = df[col].dropna()
            for val in non_null_series.iloc[:10]:
                val_str = str(val).strip()
                if val_str and val_str not in samples and val_str.lower() != 'nan':
                    samples.append(val_str[:40])
                if len(samples) >= 3:
                    break

        df_cols_info.append({
            'original': col_str,
            'normalized': norm_col,
            'samples': samples
        })

    assigned_targets = set()
    assigned_cols = set()

    # Step 1: Apply manual mappings if specified
    for item in df_cols_info:
        orig = item['original']
        if orig in manual_mapping and manual_mapping[orig]:
            target = manual_mapping[orig].strip()
            if target in SCHEMA_TARGETS and target not in assigned_targets:
                target_to_original[target] = orig
                original_to_target[orig] = target
                assigned_targets.add(target)
                assigned_cols.add(orig)

    # Step 2: Intelligent Date Detection:
    # Separate Occurrence Date from Report Date
    if 'incident_date' not in assigned_targets:
        occurrence_aliases = [
            'date_of_occurrence', 'crime_date', 'incident_date', 'occurrence_date',
            'date_occurred', 'occurred_date', 'event_date', 'incident_datetime'
        ]
        report_aliases = [
            'date_reported', 'reported_date', 'report_date', 'date_of_report',
            'filing_date', 'complaint_date', 'lodged_date', 'registration_date'
        ]

        occ_col_found = None
        rep_col_found = None
        generic_date_col = None

        for item in df_cols_info:
            orig = item['original']
            norm = item['normalized']
            if orig in assigned_cols:
                continue

            if norm in occurrence_aliases:
                occ_col_found = orig
            elif norm in report_aliases:
                rep_col_found = orig
            elif norm in ['date', 'datetime', 'timestamp', 'incident_day']:
                generic_date_col = orig

        # Prefer Date of Occurrence over Date Reported
        if occ_col_found:
            target_to_original['incident_date'] = occ_col_found
            original_to_target[occ_col_found] = 'incident_date'
            assigned_targets.add('incident_date')
            assigned_cols.add(occ_col_found)
            if rep_col_found:
                target_to_original['report_date'] = rep_col_found
                original_to_target[rep_col_found] = 'report_date'
                assigned_targets.add('report_date')
                assigned_cols.add(rep_col_found)
                friendly_notes.append(
                    f"Selected '{occ_col_found}' as Date of Occurrence (preserving '{rep_col_found}' as Date Reported)."
                )
        elif generic_date_col:
            target_to_original['incident_date'] = generic_date_col
            original_to_target[generic_date_col] = 'incident_date'
            assigned_targets.add('incident_date')
            assigned_cols.add(generic_date_col)
            if rep_col_found:
                target_to_original['report_date'] = rep_col_found
                original_to_target[rep_col_found] = 'report_date'
                assigned_targets.add('report_date')
                assigned_cols.add(rep_col_found)
        elif rep_col_found:
            # ONLY Date Reported was found! Do not silently substitute as incident date.
            target_to_original['report_date'] = rep_col_found
            original_to_target[rep_col_found] = 'report_date'
            assigned_targets.add('report_date')
            assigned_cols.add(rep_col_found)
            ambiguities.append({
                'target_field': 'incident_date',
                'type': 'report_date_only',
                'detected_column': rep_col_found,
                'friendly_field': 'Incident Date',
                'message': (
                    f"We detected the column '{rep_col_found}' (Date Reported), but no Date of Occurrence was found. "
                    f"To maintain forensic accuracy, please confirm if you wish to use '{rep_col_found}' as the incident date."
                ),
            })

    # Step 3: Exact alias matching for remaining targets
    for target in priority_order:
        if target in assigned_targets:
            continue
        target_aliases = [normalize_header(a) for a in SCHEMA_TARGETS[target]['aliases']]

        for item in df_cols_info:
            orig = item['original']
            norm = item['normalized']
            if orig in assigned_cols:
                continue

            if norm in target_aliases:
                target_to_original[target] = orig
                original_to_target[orig] = target
                assigned_targets.add(target)
                assigned_cols.add(orig)
                break

    # Step 4: Token-based disambiguation for unassigned targets
    for target in priority_order:
        if target in assigned_targets:
            continue

        for item in df_cols_info:
            orig = item['original']
            norm = item['normalized']
            if orig in assigned_cols:
                continue

            matched = False
            if target == 'crime_category':
                if any(k in norm for k in ['crime_type', 'offense_type', 'crime_category', 'charge_desc', 'crime_name']) or norm == 'crime':
                    matched = True
            elif target == 'location':
                if any(k in norm for k in ['neighborhood', 'jurisdiction', 'location_name', 'incident_loc']) or norm in ['area', 'place']:
                    matched = True
            elif target == 'incident_time':
                if any(k in norm for k in ['incident_time', 'crime_time', 'occurred_time']) and 'date' not in norm:
                    matched = True
            elif target == 'crime_code':
                if any(k in norm for k in ['crime_code', 'offense_code', 'charge_code', 'ipc_section', 'penal_code']) or norm in ['code', 'crime_id']:
                    matched = True
            elif target == 'victim_age':
                if any(k in norm for k in ['victim_age', 'age_of_victim', 'vic_age']) or norm == 'age':
                    matched = True
            elif target == 'victim_gender':
                if any(k in norm for k in ['victim_gender', 'victim_sex', 'vic_gender', 'vic_sex']) or norm in ['gender', 'sex']:
                    matched = True
            elif target == 'weapon_used':
                if any(k in norm for k in ['weapon_used', 'weapon_type', 'weapon_desc', 'arms_used']) or norm in ['weapon', 'arms']:
                    matched = True
            elif target == 'description':
                if any(k in norm for k in ['narrative', 'incident_desc', 'incident_detail', 'modus_operandi']):
                    matched = True
            elif target == 'latitude':
                if norm in ['lat', 'latitude_deg', 'gps_lat']:
                    matched = True
            elif target == 'longitude':
                if norm in ['lng', 'lon', 'longitude_deg', 'gps_lon', 'gps_lng']:
                    matched = True
            elif target == 'status':
                if any(k in norm for k in ['status', 'disposition', 'resolution']):
                    matched = True
            elif target == 'source':
                if any(k in norm for k in ['station', 'agency', 'reporting_dept', 'police_dept']):
                    matched = True

            if matched:
                target_to_original[target] = orig
                original_to_target[orig] = target
                assigned_targets.add(target)
                assigned_cols.add(orig)
                break

    # Step 5: Construct friendly detected fields summary
    detected_fields_summary = []
    for target in priority_order:
        if target in target_to_original:
            orig = target_to_original[target]
            info = SCHEMA_TARGETS[target]
            col_item = next((c for c in df_cols_info if c['original'] == orig), None)
            samples = col_item['samples'] if col_item else []
            detected_fields_summary.append({
                'target_field': target,
                'friendly_name': info['friendly_name'],
                'label': info['label'],
                'original_column': orig,
                'is_required': info['required'],
                'sample_values': samples,
                'confidence': 'manual' if (orig in manual_mapping) else 'high'
            })

    # Step 6: Construct detailed column-by-column mappings
    for item in df_cols_info:
        orig = item['original']
        norm = item['normalized']
        mapped_target = original_to_target.get(orig)

        if mapped_target:
            confidence = 'manual' if (orig in manual_mapping) else 'high'
            target_info = SCHEMA_TARGETS[mapped_target]
            column_mappings.append({
                'original_name': orig,
                'normalized_name': norm,
                'target_field': mapped_target,
                'target_label': target_info['label'],
                'friendly_name': target_info['friendly_name'],
                'is_required': target_info['required'],
                'confidence': confidence,
                'confidence_badge': 'success' if confidence in ['high', 'manual'] else 'warning',
                'description': target_info['description'],
                'sample_values': item['samples'],
            })
        else:
            unmapped_columns.append(orig)
            column_mappings.append({
                'original_name': orig,
                'normalized_name': norm,
                'target_field': None,
                'target_label': 'Unmapped / Skipped',
                'friendly_name': 'Unmapped Column',
                'is_required': False,
                'confidence': 'unmapped',
                'confidence_badge': 'secondary',
                'description': 'Safely ignored during ingestion (not part of crime schema)',
                'sample_values': item['samples'],
            })

    missing_required = [req for req in REQUIRED_COLUMNS if req not in target_to_original]

    if not missing_required and not ambiguities:
        confidence_summary = 'high'
    elif len(missing_required) < len(REQUIRED_COLUMNS):
        confidence_summary = 'medium'
    else:
        confidence_summary = 'incomplete'

    return {
        'column_mappings': column_mappings,
        'target_to_original': target_to_original,
        'original_to_target': original_to_target,
        'missing_required': missing_required,
        'unmapped_columns': unmapped_columns,
        'confidence_summary': confidence_summary,
        'ambiguities': ambiguities,
        'detected_fields_summary': detected_fields_summary,
        'friendly_notes': friendly_notes,
    }


def validate_dataset(df, custom_mapping=None):
    """
    Validates dataset structure:
    - Runs automatic column detection with alias taxonomy
    - Detects empty values, duplicates, and invalid dates
    - Separates valid and invalid records
    - Does NOT reject the dataset if only a few rows are invalid
    - Explains validation issues in simple, human language
    """
    errors = []
    warnings = []

    if df is None or df.empty:
        errors.append("The uploaded dataset contains no data rows or is completely empty.")
        return False, errors, warnings, {}, {'total': 0, 'valid': 0, 'invalid': 0, 'duplicates': 0}

    # Run Smart Column Detection
    mapping_info = detect_column_mapping(df, manual_mapping=custom_mapping)
    target_to_original = mapping_info['target_to_original']
    missing_required = mapping_info['missing_required']
    ambiguities = mapping_info.get('ambiguities', [])

    # Check for missing required columns
    if missing_required:
        missing_friendly = [SCHEMA_TARGETS[r]['friendly_name'] for r in missing_required]
        errors.append(
            f"Could not automatically detect column(s) for: {', '.join(missing_friendly)}. "
            f"Please select the corresponding column(s) below to continue."
        )

    # Check for duplicate rows
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        warnings.append(
            f"Detected {dup_count} duplicate row(s). "
            f"The system will automatically deduplicate and retain a single clean record for each."
        )

    # Date parsing check if date column was mapped
    invalid_date_count = 0
    date_format_detected = "Standard Date"
    if 'incident_date' in target_to_original:
        date_col = target_to_original['incident_date']
        parsed_dates, inv_idx, inv_exp, detected_fmt, is_ambig = parse_date_series(df[date_col])
        invalid_date_count = len(inv_idx)
        date_format_detected = detected_fmt
        mapping_info['detected_date_format'] = detected_fmt
        if is_ambig:
            warnings.append(
                f"Dates in '{date_col}' follow a slash/dash format. "
                f"They were parsed using standard day-first calendar notation (DD/MM/YYYY)."
            )
        if invalid_date_count > 0:
            warnings.append(
                f"{invalid_date_count} row(s) contain invalid or missing dates in column '{date_col}'. "
                f"These incomplete rows will be excluded while all valid rows will be imported."
            )

    # Empty category check
    empty_cat_count = 0
    if 'crime_category' in target_to_original:
        cat_col = target_to_original['crime_category']
        empty_cat_count = int(df[cat_col].isna().sum() + (df[cat_col].astype(str).str.strip().isin(['', 'nan', 'none', 'null'])).sum())
        if empty_cat_count > 0:
            warnings.append(
                f"{empty_cat_count} row(s) have an empty Crime Offense category."
            )

    # Empty location check
    empty_loc_count = 0
    if 'location' in target_to_original:
        loc_col = target_to_original['location']
        empty_loc_count = int(df[loc_col].isna().sum() + (df[loc_col].astype(str).str.strip().isin(['', 'nan', 'none', 'null'])).sum())
        if empty_loc_count > 0:
            warnings.append(
                f"{empty_loc_count} row(s) have an empty Location/Area."
            )

    total_rows = len(df)
    estimated_invalid = max(invalid_date_count, empty_cat_count, empty_loc_count)
    estimated_valid = max(0, total_rows - estimated_invalid - dup_count)

    quality_stats = {
        'total': total_rows,
        'valid': estimated_valid,
        'invalid': estimated_invalid,
        'duplicates': dup_count,
        'invalid_date_count': invalid_date_count,
        'empty_cat_count': empty_cat_count,
        'empty_loc_count': empty_loc_count,
        'detected_date_format': date_format_detected,
    }

    # is_valid is True if no required columns are missing and no unresolved ambiguities
    is_valid = (len(missing_required) == 0 and len(ambiguities) == 0)

    return is_valid, errors, warnings, mapping_info, quality_stats


def clean_dataset(df, column_mapping=None):
    """
    Cleans and standardizes the uploaded DataFrame:
    - Normalizes column names to internal schema targets using automatic/custom mapping
    - Strips whitespace
    - Drops duplicate rows
    - Standardizes date formats to ISO YYYY-MM-DD
    - Standardizes severity and status choices
    - Preserves unmapped columns without silently altering unrelated data
    """
    df_cleaned = df.copy()

    if column_mapping is None or not isinstance(column_mapping, dict):
        mapping_result = detect_column_mapping(df)
        column_mapping = mapping_result['original_to_target']

    # Rename original columns to target schema names
    rename_dict = {orig: target for orig, target in column_mapping.items() if target}
    df_cleaned.rename(columns=rename_dict, inplace=True)

    # Deduplicate rows
    initial_rows = len(df_cleaned)
    df_cleaned.drop_duplicates(inplace=True)
    dropped_dupes = initial_rows - len(df_cleaned)
    if dropped_dupes > 0:
        logger.info(f"Cleaned dataset: removed {dropped_dupes} duplicate rows.")

    # Strip whitespace from string columns
    for col in df_cleaned.select_dtypes(include=['object']):
        df_cleaned[col] = df_cleaned[col].astype(str).str.strip()

    # Intelligently parse dates in incident_date
    if 'incident_date' in df_cleaned.columns:
        parsed_dates, _, _, _, _ = parse_date_series(df_cleaned['incident_date'])
        df_cleaned['incident_date'] = parsed_dates

    # Standardize severity
    valid_severities = ['low', 'medium', 'high', 'critical']
    if 'severity' in df_cleaned.columns:
        df_cleaned['severity'] = df_cleaned['severity'].fillna('medium').astype(str).str.lower().str.strip()
        df_cleaned['severity'] = df_cleaned['severity'].apply(
            lambda s: s if s in valid_severities else 'medium'
        )
    else:
        df_cleaned['severity'] = 'medium'

    # Standardize status
    valid_statuses = ['reported', 'under_investigation', 'solved', 'closed']
    if 'status' in df_cleaned.columns:
        df_cleaned['status'] = (
            df_cleaned['status']
            .fillna('reported')
            .astype(str)
            .str.lower()
            .str.replace(' ', '_')
            .str.strip()
        )
        df_cleaned['status'] = df_cleaned['status'].apply(
            lambda s: s if s in valid_statuses else 'reported'
        )
    else:
        df_cleaned['status'] = 'reported'

    # Coordinates validation
    for coord_col in ['latitude', 'longitude']:
        if coord_col in df_cleaned.columns:
            df_cleaned[coord_col] = pd.to_numeric(df_cleaned[coord_col], errors='coerce')

    return df_cleaned


def get_data_quality_stats(df, mapping=None):
    """
    Returns preliminary data quality metrics for the preview interface.
    """
    total = len(df)
    missing_values = int(df.isnull().sum().sum())
    duplicates = int(df.duplicated().sum())

    if mapping:
        req_cols = [mapping[k] for k in REQUIRED_COLUMNS if k in mapping and mapping[k] in df.columns]
    else:
        req_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]

    if len(req_cols) == len(REQUIRED_COLUMNS):
        valid_rows_mask = df[req_cols].notnull().all(axis=1)
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


def process_dataset(upload_instance, df, custom_mapping=None):
    """
    Processes the uploaded DataFrame and creates CrimeRecord instances.
    Extracts actual location data and preserves original location strings.
    Separates valid and invalid records without rejecting the entire dataset.
    Updates DatasetUpload status, record counts, and synchronizes the ontology graph.
    """
    upload_instance.status = 'processing'
    upload_instance.save(update_fields=['status'])

    # Validation & Mapping
    is_valid, errors_list, warnings_list, mapping_info, quality_stats = validate_dataset(df, custom_mapping=custom_mapping)

    cleaned_df = clean_dataset(df, column_mapping=mapping_info['original_to_target'])
    total_rows = len(cleaned_df)
    valid_count = 0
    invalid_count = 0
    invalid_row_details = []

    # Cache categories and locations for quick lookup
    categories = {c.name.lower(): c for c in CrimeCategory.objects.all()}
    locations = {f"{l.name.lower()}::{l.city.lower()}": l for l in Location.objects.all()}
    locations_by_name = {l.name.lower(): l for l in Location.objects.all()}

    records_to_create = []
    exact_coords_count = 0
    approx_coords_count = 0
    approx_cities = set()

    for idx, row in cleaned_df.iterrows():
        row_num = idx + 1
        cat_name = str(row.get('crime_category', '')).strip()
        loc_name = str(
            row.get('location') or
            row.get('location_name') or
            row.get('neighborhood') or
            row.get('area') or
            row.get('place') or
            ''
        ).strip()
        date_val = row.get('incident_date')

        # Check required fields with clear human explanations
        if not cat_name or cat_name.lower() in ['nan', 'none', '']:
            invalid_count += 1
            invalid_row_details.append({
                'row': row_num,
                'field': 'Crime Category',
                'issue': 'Missing Crime Category: The crime offense category was missing or blank.'
            })
            continue

        if not loc_name or loc_name.lower() in ['nan', 'none', '']:
            invalid_count += 1
            invalid_row_details.append({
                'row': row_num,
                'field': 'Location',
                'issue': 'Missing Location: The location or area name was missing or blank.'
            })
            continue

        if date_val is None or pd.isnull(date_val) or not isinstance(date_val, (date, datetime)):
            invalid_count += 1
            orig_date = row.get('incident_date')
            invalid_row_details.append({
                'row': row_num,
                'field': 'Incident Date',
                'issue': f'Invalid Date: "{orig_date}" could not be recognized as a valid calendar date.'
            })
            continue

        # Resolve Crime Category
        category = categories.get(cat_name.lower())
        if not category:
            category = CrimeCategory.objects.create(
                name=cat_name.title(),
                description=f"Auto-generated category for {cat_name.title()}",
                color_code='#1769FF'
            )
            categories[cat_name.lower()] = category

        # Resolve Location & City
        city_val = str(row.get('city') or row.get('district') or row.get('area') or loc_name).strip().title()
        state_val = str(row.get('state', 'Andhra Pradesh')).strip().title()

        loc_key = f"{loc_name.lower()}::{city_val.lower()}"
        location = locations.get(loc_key) or locations_by_name.get(loc_name.lower())

        if not location:
            lat = row.get('latitude')
            lng = row.get('longitude')

            has_exact_coords = (
                pd.notnull(lat) and pd.notnull(lng) and
                -90 <= float(lat) <= 90 and -180 <= float(lng) <= 180
            )

            if has_exact_coords:
                lat_f = float(lat)
                lng_f = float(lng)
                exact_coords_count += 1
            else:
                fallback = (
                    KNOWN_COORDINATES.get(loc_name.lower()) or
                    KNOWN_COORDINATES.get(city_val.lower()) or
                    (20.5937, 78.9629)
                )
                lat_f, lng_f = fallback
                approx_coords_count += 1
                approx_cities.add(city_val)

            location = Location.objects.create(
                name=loc_name.title(),
                city=city_val,
                state=state_val,
                latitude=lat_f,
                longitude=lng_f,
                region_type='urban'
            )
            locations[loc_key] = location
            locations_by_name[loc_name.lower()] = location
        else:
            exact_coords_count += 1

        # Parse time if provided
        incident_time = None
        raw_time = row.get('incident_time')
        if pd.notnull(raw_time) and str(raw_time).lower() not in ['nan', 'nat', 'none', '']:
            try:
                if isinstance(raw_time, str):
                    clean_time = raw_time.strip()
                    for t_fmt in ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']:
                        try:
                            incident_time = datetime.strptime(clean_time, t_fmt).time()
                            break
                        except ValueError:
                            pass
                elif hasattr(raw_time, 'strftime') and hasattr(raw_time, 'hour'):
                    incident_time = raw_time
            except Exception:
                incident_time = None

        incident_date = date_val if isinstance(date_val, date) else date_val.date()

        # Build narrative description enriched with detected optional fields
        extra_info = []
        if pd.notnull(row.get('crime_code')) and str(row.get('crime_code')).strip() not in ['', 'nan', 'none']:
            extra_info.append(f"Crime Code: {str(row.get('crime_code')).strip()}")
        if pd.notnull(row.get('victim_age')) and str(row.get('victim_age')).strip() not in ['', 'nan', 'none']:
            extra_info.append(f"Victim Age: {str(row.get('victim_age')).strip()}")
        if pd.notnull(row.get('victim_gender')) and str(row.get('victim_gender')).strip() not in ['', 'nan', 'none']:
            extra_info.append(f"Victim Gender: {str(row.get('victim_gender')).strip()}")
        if pd.notnull(row.get('weapon_used')) and str(row.get('weapon_used')).strip() not in ['', 'nan', 'none']:
            extra_info.append(f"Weapon: {str(row.get('weapon_used')).strip()}")

        desc_raw = str(row.get('description', '')).strip()
        if extra_info:
            details_str = " | ".join(extra_info)
            if desc_raw and desc_raw.lower() not in ['nan', 'none', 'incident details not provided', '']:
                final_desc = f"{desc_raw} [{details_str}]"
            else:
                final_desc = f"Incident Report: {details_str}"
        else:
            final_desc = desc_raw if (desc_raw and desc_raw.lower() not in ['nan', 'none', '']) else 'Incident details not provided'

        record = CrimeRecord(
            category=category,
            location=location,
            incident_date=incident_date,
            incident_time=incident_time,
            description=final_desc[:500],
            severity=str(row.get('severity', 'medium')),
            status=str(row.get('status', 'reported')),
            source=str(row.get('source', upload_instance.original_filename))[:200],
            dataset_upload=upload_instance
        )
        records_to_create.append(record)
        valid_count += 1

        if len(records_to_create) >= 500:
            CrimeRecord.objects.bulk_create(records_to_create)
            records_to_create = []

    if records_to_create:
        CrimeRecord.objects.bulk_create(records_to_create)

    # Compute Quality Health Score
    quality_score = round((valid_count / max(1, total_rows)) * 100, 1)

    location_audit = {
        'exact_coords': exact_coords_count,
        'approx_coords': approx_coords_count,
        'approx_cities': list(approx_cities),
        'summary': (
            f"{exact_coords_count} record(s) with exact GPS coordinates. "
            f"{approx_coords_count} record(s) assigned verified regional centroids for {', '.join(list(approx_cities)[:3]) or 'regional centers'} (no coordinates were invented)."
            if approx_coords_count > 0 else
            f"All {exact_coords_count} record(s) contain exact GPS coordinates."
        )
    }

    upload_instance.total_records = len(df)
    upload_instance.valid_records = valid_count
    upload_instance.invalid_records = invalid_count
    upload_instance.status = 'completed' if valid_count > 0 else 'failed'
    upload_instance.validation_errors = {
        'column_mapping': mapping_info.get('column_mappings', []),
        'target_to_original': mapping_info.get('target_to_original', {}),
        'original_to_target': mapping_info.get('original_to_target', {}),
        'unmapped_columns': mapping_info.get('unmapped_columns', []),
        'detected_fields_summary': mapping_info.get('detected_fields_summary', []),
        'detected_date_format': mapping_info.get('detected_date_format', 'Standard Date'),
        'invalid_row_details': invalid_row_details[:100],
        'location_audit': location_audit,
        'warnings': warnings_list,
        'duplicates_removed': quality_stats.get('duplicates', 0),
        'quality_score': quality_score,
    }
    upload_instance.processing_notes = (
        f"Processed {total_rows} total rows. Successfully imported {valid_count} records ({quality_score}% clean). "
        f"Skipped {invalid_count} incomplete rows. Duplicates resolved: {quality_stats.get('duplicates', 0)}."
    )
    upload_instance.processed_at = timezone.now()
    upload_instance.save()

    # Synchronize records to the ontology knowledge graph
    try:
        from ontology.utils import sync_dataset_to_ontology
        sync_dataset_to_ontology()
    except Exception as onto_err:
        logger.warning(f"Could not automatically sync ontology after upload: {onto_err}")

    logger.info(f"Dataset upload {upload_instance.id} processed: {valid_count} valid, {invalid_count} invalid.")
    return upload_instance
