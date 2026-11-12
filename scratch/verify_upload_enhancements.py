import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
import pandas as pd
import io
from datetime import date, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.test_settings')
django.setup()

from django.core.management import call_command
call_command('migrate', verbosity=0)

from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from crime_data.models import CrimeRecord, DatasetUpload, CrimeCategory, Location
from crime_data.utils import detect_column_mapping, validate_dataset, clean_dataset, process_dataset

def run_checks():
    print("=== STARTING DATASET UPLOAD & VALIDATION ENHANCEMENT VERIFICATION ===")

    # Test 1: Column Detection with extensive aliases
    print("\n[TEST 1] Testing Automatic Column Detection & Taxonomy...")
    test_df = pd.DataFrame({
        'Crime Type': ['Robbery', 'Burglary', 'Assault'],
        'Date of Occurrence': ['2024-06-01', '2024-06-02', '2024-06-03'],
        'Neighborhood': ['Downtown Core', 'West End', 'Harbor View'],
        'City Name': ['Rajahmundry', 'Vijayawada', 'Visakhapatnam'],
        'GPS Lat': [17.0005, 16.5062, 17.6868],
        'GPS Lng': [81.8040, 80.6480, 83.2185],
        'Incident Severity': ['High', 'Medium', 'Critical'],
        'Resolution Status': ['Under Investigation', 'Reported', 'Solved'],
        'Modus Operandi': ['Smashed glass entry', 'Forced front door', 'Street dispute'],
        'Reporting Station': ['Station A', 'Station B', 'Station C'],
        'Officer ID': ['Badge 101', 'Badge 102', 'Badge 103'], # Unrelated column
        'Weather Condition': ['Clear', 'Rain', 'Fog'] # Unrelated column
    })

    mapping = detect_column_mapping(test_df)
    t2o = mapping['target_to_original']
    print(f"Detected mappings: {t2o}")

    assert t2o.get('crime_category') == 'Crime Type', f"Failed crime_category mapping: {t2o.get('crime_category')}"
    assert t2o.get('incident_date') == 'Date of Occurrence', f"Failed incident_date mapping: {t2o.get('incident_date')}"
    assert t2o.get('location') == 'Neighborhood', f"Failed location mapping: {t2o.get('location')}"
    assert t2o.get('latitude') == 'GPS Lat', f"Failed latitude mapping: {t2o.get('latitude')}"
    assert t2o.get('longitude') == 'GPS Lng', f"Failed longitude mapping: {t2o.get('longitude')}"
    assert t2o.get('severity') == 'Incident Severity', f"Failed severity mapping: {t2o.get('severity')}"
    assert t2o.get('status') == 'Resolution Status', f"Failed status mapping: {t2o.get('status')}"
    assert t2o.get('description') == 'Modus Operandi', f"Failed description mapping: {t2o.get('description')}"
    assert t2o.get('source') == 'Reporting Station', f"Failed source mapping: {t2o.get('source')}"
    
    # Assert unrelated columns are NOT mapped
    assert 'Officer ID' in mapping['unmapped_columns'], "Officer ID should be unmapped!"
    assert 'Weather Condition' in mapping['unmapped_columns'], "Weather Condition should be unmapped!"
    assert 'Officer ID' not in mapping['original_to_target'], "Officer ID should not be in target map!"
    print("[OK] Column detection correctly recognized all aliases and ignored unrelated columns.")

    # Test 2: Validation with duplicate detection and quality scores
    print("\n[TEST 2] Testing Flexible Validation & Quality Stats...")
    dup_df = pd.concat([test_df, test_df.iloc[[0]]], ignore_index=True) # add 1 duplicate row
    is_valid, errors, warnings, mapping_info, quality_stats = validate_dataset(dup_df)
    assert is_valid is True, f"Validation should succeed with alias headers, errors: {errors}"
    assert quality_stats['duplicates'] == 1, f"Expected 1 duplicate, got {quality_stats['duplicates']}"
    assert any("duplicate" in w.lower() for w in warnings), "Expected duplicate warning"
    print(f"[OK] Validation passed: total={quality_stats['total']}, duplicates={quality_stats['duplicates']}, warnings={len(warnings)}")

    # Test 3: Preprocessing & Cleaning
    print("\n[TEST 3] Testing Data Preprocessing & Date Normalization...")
    cleaned = clean_dataset(dup_df)
    assert len(cleaned) == 3, f"Cleaned dataset should have deduplicated 4 down to 3 rows, got {len(cleaned)}"
    assert 'crime_category' in cleaned.columns
    assert 'incident_date' in cleaned.columns
    assert all(isinstance(d, (date, datetime)) for d in cleaned['incident_date'].dropna())
    assert cleaned['severity'].iloc[0] == 'high'
    print("[OK] Preprocessing deduplicated rows and standardized date and severity fields.")

    # Test 4: End-to-end Client Upload & Ingestion
    print("\n[TEST 4] Testing End-to-end Client Upload & Downstream Integration...")
    client = Client()
    user, _ = User.objects.get_or_create(username='analyst_e2e', defaults={'role': 'analyst', 'email': 'e2e@crime.org'})
    client.force_login(user)

    csv_data = (
        "Offense,Area,Date of Occurrence,GPS Lat,GPS Lng,Severity\n"
        "Cyber Fraud,Cyberabad,2024-07-01,17.4401,78.3489,high\n"
        "Homicide,Old City,2024-07-02,17.3616,78.4747,critical\n"
        "Vehicle Theft,Secunderabad,2024-07-03,17.4399,78.4983,medium\n"
    )
    upload_file = SimpleUploadedFile("telangana_crime_sample.csv", csv_data.encode('utf-8'), content_type="text/csv")
    upload_resp = client.post(reverse('crime_data:upload_dataset'), {'file': upload_file}, follow=True)
    assert upload_resp.status_code == 200, f"Upload POST failed: {upload_resp.status_code}"

    latest_upload = DatasetUpload.objects.latest('id')
    assert latest_upload.status == 'completed', f"Upload status expected completed, got {latest_upload.status}"
    assert latest_upload.valid_records == 3, f"Expected 3 valid records, got {latest_upload.valid_records}"

    # Verify Preview View renders
    preview_url = reverse('crime_data:dataset_preview', kwargs={'pk': latest_upload.id})
    prev_resp = client.get(preview_url)
    assert prev_resp.status_code == 200
    assert b"Cyber Fraud" in prev_resp.content
    assert b"Column Recognition" in prev_resp.content
    print("[OK] Client upload and preview view verified.")

    # Verify Cleaned CSV Download
    download_url = reverse('crime_data:download_cleaned', kwargs={'pk': latest_upload.id})
    dl_resp = client.get(download_url)
    assert dl_resp.status_code == 200
    assert dl_resp['Content-Type'] == 'text/csv'
    assert b"Cyber Fraud" in dl_resp.content
    print("[OK] Cleaned CSV download verified.")

    # Verify Sample CSV Template Download
    template_url = reverse('crime_data:download_template')
    tpl_resp = client.get(template_url)
    assert tpl_resp.status_code == 200
    assert b"crime_category,location,city" in tpl_resp.content
    print("[OK] Standardized CSV template download verified.")

    # Test 5: Verify Downstream Integration
    print("\n[TEST 5] Testing Integration with Downstream Modules...")
    # 5.1 Analysis page
    analysis_resp = client.get(reverse('analysis:analysis'))
    assert analysis_resp.status_code == 200, f"Analysis page failed: {analysis_resp.status_code}"
    print("[OK] Analysis module integrated.")

    # 5.2 Location Analysis page
    loc_resp = client.get(reverse('location_analysis:map'))
    assert loc_resp.status_code == 200, f"Location analysis failed: {loc_resp.status_code}"
    print("[OK] Location analysis module integrated.")

    # 5.3 Crime Patterns page
    pat_resp = client.get(reverse('patterns:patterns'))
    assert pat_resp.status_code == 200, f"Patterns module failed: {pat_resp.status_code}"
    print("[OK] Patterns module integrated.")

    # 5.4 Model Training page
    train_resp = client.get(reverse('model_training:train'))
    assert train_resp.status_code == 200, f"Model training module failed: {train_resp.status_code}"
    print("[OK] Model training module integrated.")

    # 5.5 Prediction Trends page
    pred_resp = client.get(reverse('prediction:prediction'))
    assert pred_resp.status_code == 200, f"Prediction module failed: {pred_resp.status_code}"
    print("[OK] Prediction module integrated.")

    # 5.6 Reports page
    rep_resp = client.get(reverse('reports:reports'))
    assert rep_resp.status_code == 200, f"Reports module failed: {rep_resp.status_code}"
    print("[OK] Reports module integrated.")

    # Test 6: Remapping functionality
    print("\n[TEST 6] Testing Manual Remap Workflow...")
    # Create an upload with ambiguous columns
    ambiguous_csv = (
        "custom_code,custom_place,custom_timestamp\n"
        "Shoplifting,Market Street,2024-08-01\n"
        "Vandalism,Park Avenue,2024-08-02\n"
    )
    amb_file = SimpleUploadedFile("ambiguous.csv", ambiguous_csv.encode('utf-8'), content_type="text/csv")
    amb_upload = DatasetUpload.objects.create(
        user=user,
        file=amb_file,
        original_filename='ambiguous.csv',
        status='pending',
        total_records=2
    )

    remap_resp = client.post(
        reverse('crime_data:remap_dataset', kwargs={'pk': amb_upload.id}),
        {
            'map_custom_code': 'crime_category',
            'map_custom_place': 'location',
            'map_custom_timestamp': 'incident_date',
        },
        follow=True
    )
    assert remap_resp.status_code == 200
    amb_upload.refresh_from_db()
    assert amb_upload.status == 'completed'
    assert amb_upload.valid_records == 2
    assert CrimeRecord.objects.filter(dataset_upload=amb_upload).count() == 2
    print("[OK] Manual remapping successfully ingested records.")

    # Test 7: Intelligent Date Detection: Occurrence vs Reported Date
    print("\n[TEST 7] Testing Intelligent Date Detection (Occurrence vs Reported)...")
    date_test_df = pd.DataFrame({
        'Date Reported': ['2024-09-20', '2024-09-21'],
        'Date of Occurrence': ['2024-09-15', '2024-09-16'],
        'Offense': ['Burglary', 'Robbery'],
        'Area': ['Kurnool', 'Guntur']
    })
    mapping7 = detect_column_mapping(date_test_df)
    assert mapping7['target_to_original']['incident_date'] == 'Date of Occurrence', "Should select Date of Occurrence over Date Reported!"
    assert mapping7['target_to_original']['report_date'] == 'Date Reported'
    assert len(mapping7.get('ambiguities', [])) == 0, "No ambiguity when occurrence date is present"
    print("[OK] Date of Occurrence preferred over Date Reported.")

    # Test 8: Report Date Only flags Ambiguity
    print("\n[TEST 8] Testing Report Date Only Ambiguity...")
    rep_only_df = pd.DataFrame({
        'Date Reported': ['2024-09-20', '2024-09-21'],
        'Crime': ['Theft', 'Assault'],
        'City': ['Tirupati', 'Nellore']
    })
    mapping8 = detect_column_mapping(rep_only_df)
    assert 'incident_date' not in mapping8['target_to_original'], "Must NOT silently use Date Reported as incident date!"
    assert len(mapping8.get('ambiguities', [])) > 0, "Must flag ambiguity for user confirmation!"
    assert mapping8['ambiguities'][0]['type'] == 'report_date_only'
    print("[OK] Report Date Only correctly flagged for user confirmation.")

    # Test 9: Mixed Valid & Invalid Rows (Partial Row Ingestion)
    print("\n[TEST 9] Testing Partial Row Validation & Separation...")
    mixed_df = pd.DataFrame({
        'Crime Type': ['Extortion', '', 'Theft', 'Robbery'],
        'Location': ['Beach Road', 'Main St', 'Railway Station', 'Market'],
        'Incident Date': ['2024-08-10', '2024-08-11', 'invalid_date', '2024-08-12'],
        'Weapon Used': ['Gun', 'None', 'Knife', 'None'],
        'Victim Age': [42, 28, 35, 19]
    })
    mixed_upload = DatasetUpload.objects.create(
        user=user,
        original_filename='mixed_quality_test.csv',
        status='pending',
        total_records=4
    )
    process_dataset(mixed_upload, mixed_df)
    mixed_upload.refresh_from_db()
    assert mixed_upload.status == 'completed', "Dataset should not be rejected because of invalid rows!"
    assert mixed_upload.valid_records == 2, f"Expected 2 valid records, got {mixed_upload.valid_records}"
    assert mixed_upload.invalid_records == 2, f"Expected 2 invalid records, got {mixed_upload.invalid_records}"
    assert CrimeRecord.objects.filter(dataset_upload=mixed_upload).count() == 2
    inv_details = mixed_upload.validation_errors.get('invalid_row_details', [])
    assert len(inv_details) == 2
    print("[OK] Ingested 2 valid rows and cleanly separated/explained 2 invalid rows.")

    # Test 10: Location Geocoding & Coordinate Identification
    print("\n[TEST 10] Testing Location Geocoding & Centroid Audit...")
    loc_audit = mixed_upload.validation_errors.get('location_audit', {})
    assert 'summary' in loc_audit
    assert loc_audit.get('approx_coords', 0) > 0, "Should identify verified regional centroids used"
    print(f"[OK] Location audit logged: {loc_audit['summary']}")

    print("\n=== ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_checks()
