from datetime import date, time
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from crime_data.models import CrimeCategory, Location, CrimeRecord, DatasetUpload


class TestCrimeCategory(TestCase):
    def test_creation(self):
        category = CrimeCategory.objects.create(
            name='Theft',
            description='Unlawful taking of property',
            color_code='#FF5733',
            icon='bi-shield'
        )
        self.assertEqual(category.name, 'Theft')
        self.assertEqual(category.color_code, '#FF5733')

    def test_unique_name_constraint(self):
        CrimeCategory.objects.create(name='Burglary')
        with self.assertRaises(Exception):
            CrimeCategory.objects.create(name='Burglary')

    def test_string_representation(self):
        category = CrimeCategory.objects.create(name='Robbery')
        self.assertEqual(str(category), 'Robbery')


class TestLocation(TestCase):
    def test_creation_with_gps_coordinates(self):
        location = Location.objects.create(
            name='Central Station',
            city='Mumbai',
            state='Maharashtra',
            country='India',
            latitude=18.969600,
            longitude=72.819300,
            region_type='urban',
            population=500000
        )
        self.assertEqual(location.name, 'Central Station')
        self.assertEqual(float(location.latitude), 18.969600)
        self.assertEqual(float(location.longitude), 72.819300)

    def test_region_type_choices(self):
        for choice, _ in Location.REGION_CHOICES:
            loc = Location.objects.create(
                name=f'{choice} Area',
                city='Delhi',
                state='Delhi',
                latitude=28.6139,
                longitude=77.2090,
                region_type=choice
            )
            self.assertEqual(loc.region_type, choice)

    def test_string_representation(self):
        location = Location.objects.create(
            name='Connaught Place',
            city='New Delhi',
            state='Delhi',
            latitude=28.6315,
            longitude=77.2167
        )
        self.assertEqual(str(location), 'Connaught Place, New Delhi, Delhi')


class TestCrimeRecord(TestCase):
    def setUp(self):
        self.category = CrimeCategory.objects.create(name='Assault')
        self.location = Location.objects.create(
            name='Downtown',
            city='Bengaluru',
            state='Karnataka',
            latitude=12.9716,
            longitude=77.5946
        )

    def test_creation_with_fk_relationships(self):
        record = CrimeRecord.objects.create(
            category=self.category,
            location=self.location,
            incident_date=date(2024, 1, 15),
            incident_time=time(14, 30),
            description='Physical altercation reported',
            severity='medium',
            status='reported',
            source='Police Dispatch'
        )
        self.assertEqual(record.category, self.category)
        self.assertEqual(record.location, self.location)
        self.assertEqual(record.description, 'Physical altercation reported')

    def test_severity_and_status_choices(self):
        for sev, _ in CrimeRecord.SEVERITY_CHOICES:
            rec = CrimeRecord.objects.create(
                category=self.category,
                location=self.location,
                incident_date=date(2024, 2, 1),
                description=f'Incident severity {sev}',
                severity=sev,
                status='reported'
            )
            self.assertEqual(rec.severity, sev)

        for stat, _ in CrimeRecord.STATUS_CHOICES:
            rec = CrimeRecord.objects.create(
                category=self.category,
                location=self.location,
                incident_date=date(2024, 2, 2),
                description=f'Incident status {stat}',
                severity='low',
                status=stat
            )
            self.assertEqual(rec.status, stat)

    def test_ordering(self):
        rec1 = CrimeRecord.objects.create(
            category=self.category,
            location=self.location,
            incident_date=date(2024, 1, 10),
            description='Earlier record'
        )
        rec2 = CrimeRecord.objects.create(
            category=self.category,
            location=self.location,
            incident_date=date(2024, 1, 20),
            description='Later record'
        )
        records = list(CrimeRecord.objects.all())
        self.assertEqual(records[0], rec2)
        self.assertEqual(records[1], rec1)


class TestCrimeListView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='vieweruser',
            email='viewer@example.com',
            password='Password123!',
            role='viewer'
        )
        self.category = CrimeCategory.objects.create(name='Vandalism')
        self.location = Location.objects.create(
            name='North District',
            city='Pune',
            state='Maharashtra',
            latitude=18.5204,
            longitude=73.8567
        )

        for i in range(30):
            CrimeRecord.objects.create(
                category=self.category,
                location=self.location,
                incident_date=date(2024, 1, 1),
                description=f'Vandalism incident #{i + 1}',
                severity='low',
                status='reported'
            )

    def test_unauthenticated_access_redirects_to_login(self):
        response = self.client.get(reverse('crime_data:record_list'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    def test_authenticated_access_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('crime_data:record_list'))
        self.assertEqual(response.status_code, 200)

    def test_pagination(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('crime_data:record_list'), {'page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('page_obj' in response.context)
        page_obj = response.context['page_obj']
        self.assertTrue(page_obj.has_next())


class TestDatasetUpload(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='analystuser',
            email='analyst@example.com',
            password='Password123!',
            role='analyst'
        )

    def test_model_creation(self):
        dummy_file = SimpleUploadedFile("crimes.csv", b"category,date,location\nTheft,2024-01-01,Station", content_type="text/csv")
        upload = DatasetUpload.objects.create(
            user=self.user,
            file=dummy_file,
            original_filename='crimes.csv',
            file_type='csv',
            total_records=1,
            valid_records=1,
            invalid_records=0,
            status='pending'
        )
        self.assertEqual(upload.original_filename, 'crimes.csv')
        self.assertEqual(upload.status, 'pending')
        self.assertEqual(upload.user, self.user)
        self.assertIn('crimes.csv', str(upload))

    def test_status_transitions(self):
        dummy_file = SimpleUploadedFile("data.csv", b"sample content", content_type="text/csv")
        upload = DatasetUpload.objects.create(
            user=self.user,
            file=dummy_file,
            original_filename='data.csv',
            status='pending'
        )
        self.assertEqual(upload.status, 'pending')

        upload.status = 'processing'
        upload.save()
        upload.refresh_from_db()
        self.assertEqual(upload.status, 'processing')

        upload.status = 'completed'
        upload.save()
        upload.refresh_from_db()
        self.assertEqual(upload.status, 'completed')

        upload.status = 'failed'
        upload.validation_errors = {'errors': ['Invalid header format']}
        upload.save()
        upload.refresh_from_db()
        self.assertEqual(upload.status, 'failed')
        self.assertIn('errors', upload.validation_errors)


class TestColumnDetectionAndMapping(TestCase):
    def test_alias_detection(self):
        import pandas as pd
        from crime_data.utils import detect_column_mapping

        df = pd.DataFrame({
            'Crime Description': ['Theft of vehicle', 'Assault'],
            'Date of Occurrence': ['2024-03-01', '2024-03-02'],
            'Neighborhood': ['Downtown Area', 'Uptown Area'],
            'Latitude': [17.0, 17.1],
            'Longitude': [81.8, 81.9],
            'Unrelated Column': ['abc', 'xyz']
        })

        mapping = detect_column_mapping(df)
        t2o = mapping['target_to_original']

        self.assertEqual(t2o.get('crime_category'), 'Crime Description')
        self.assertEqual(t2o.get('incident_date'), 'Date of Occurrence')
        self.assertEqual(t2o.get('location'), 'Neighborhood')
        self.assertNotIn('Unrelated Column', mapping['original_to_target'])
        self.assertIn('Unrelated Column', mapping['unmapped_columns'])
        self.assertEqual(mapping['missing_required'], [])

    def test_flexible_validation(self):
        import pandas as pd
        from crime_data.utils import validate_dataset

        # Dataset with alias names
        df = pd.DataFrame({
            'Offense': ['Robbery', 'Burglary'],
            'Incident Date': ['2024-01-01', '2024-01-02'],
            'Area': ['Sector 5', 'Sector 9'],
        })

        is_valid, errors, warnings, mapping_info, quality_stats = validate_dataset(df)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertEqual(quality_stats['total'], 2)

    def test_missing_required_columns(self):
        import pandas as pd
        from crime_data.utils import validate_dataset

        # Dataset missing location
        df = pd.DataFrame({
            'Offense': ['Robbery'],
            'Incident Date': ['2024-01-01'],
            'Random Data': ['Unknown'],
        })

        is_valid, errors, warnings, mapping_info, quality_stats = validate_dataset(df)
        self.assertFalse(is_valid)
        self.assertIn('location', mapping_info['missing_required'])


class TestUploadWorkflowIntegration(TestCase):
    def setUp(self):
        self.client = Client()
        self.analyst = User.objects.create_user(
            username='lead_analyst',
            email='lead@example.com',
            password='Password123!',
            role='analyst'
        )
        self.client.force_login(self.analyst)

    def test_upload_with_alias_headers(self):
        csv_content = (
            b"Crime Type,Date of Occurrence,Neighborhood,GPS Lat,GPS Lng,Severity\n"
            b"Robbery,2024-04-10,Rajahmundry,17.0005,81.8040,high\n"
            b"Theft,2024-04-11,Vijayawada,16.5062,80.6480,medium\n"
        )
        file_obj = SimpleUploadedFile("alias_crimes.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse('crime_data:upload_dataset'), {'file': file_obj}, follow=True)

        self.assertEqual(response.status_code, 200)
        upload = DatasetUpload.objects.latest('id')
        self.assertEqual(upload.status, 'completed')
        self.assertEqual(upload.valid_records, 2)
        self.assertEqual(CrimeRecord.objects.filter(dataset_upload=upload).count(), 2)

    def test_download_template(self):
        response = self.client.get(reverse('crime_data:download_template'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn(b'crime_category,location,city', response.content)

    def test_remap_dataset(self):
        csv_content = (
            b"col_a,col_b,col_c\n"
            b"Assault,2024-05-01,Central Park\n"
            b"Vandalism,2024-05-02,City Center\n"
        )
        file_obj = SimpleUploadedFile("custom_headers.csv", csv_content, content_type="text/csv")
        upload = DatasetUpload.objects.create(
            user=self.analyst,
            file=file_obj,
            original_filename='custom_headers.csv',
            status='pending',
            total_records=2
        )

        remap_data = {
            'map_col_a': 'crime_category',
            'map_col_b': 'incident_date',
            'map_col_c': 'location',
        }
        response = self.client.post(
            reverse('crime_data:remap_dataset', kwargs={'pk': upload.pk}),
            remap_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        upload.refresh_from_db()
        self.assertEqual(upload.status, 'completed')
        self.assertEqual(upload.valid_records, 2)
        self.assertEqual(CrimeRecord.objects.filter(dataset_upload=upload).count(), 2)

    def test_download_cleaned_dataset(self):
        cat = CrimeCategory.objects.create(name='Extortion')
        loc = Location.objects.create(name='Marina', city='Chennai', latitude=13.0, longitude=80.0)
        upload = DatasetUpload.objects.create(
            user=self.analyst,
            original_filename='extortion_data.csv',
            status='completed',
            valid_records=1
        )
        CrimeRecord.objects.create(
            category=cat,
            location=loc,
            incident_date=date(2024, 6, 1),
            dataset_upload=upload,
            description='Test extortion incident'
        )

        response = self.client.get(reverse('crime_data:download_cleaned', kwargs={'pk': upload.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Extortion', response.content)
        self.assertIn(b'Marina', response.content)


class TestIntelligentDateAndLocationDetection(TestCase):
    def test_prefer_occurrence_date_over_reported_date(self):
        import pandas as pd
        from crime_data.utils import detect_column_mapping

        df = pd.DataFrame({
            'Date Reported': ['2024-05-20', '2024-05-21'],
            'Date of Occurrence': ['2024-05-15', '2024-05-16'],
            'Crime Category': ['Theft', 'Burglary'],
            'Location': ['Central Market', 'Main St'],
        })

        mapping = detect_column_mapping(df)
        t2o = mapping['target_to_original']

        # Occurrence Date must be selected for incident_date
        self.assertEqual(t2o.get('incident_date'), 'Date of Occurrence')
        self.assertEqual(t2o.get('report_date'), 'Date Reported')
        self.assertEqual(len(mapping.get('ambiguities', [])), 0)

    def test_report_date_only_flags_ambiguity_not_silent_substitution(self):
        import pandas as pd
        from crime_data.utils import detect_column_mapping

        df = pd.DataFrame({
            'Date Reported': ['2024-05-20', '2024-05-21'],
            'Crime Type': ['Theft', 'Burglary'],
            'City': ['Mumbai', 'Delhi'],
        })

        mapping = detect_column_mapping(df)
        t2o = mapping['target_to_original']

        # incident_date must NOT be silently assigned
        self.assertNotIn('incident_date', t2o)
        self.assertEqual(t2o.get('report_date'), 'Date Reported')
        self.assertTrue(len(mapping.get('ambiguities', [])) > 0)
        self.assertEqual(mapping['ambiguities'][0]['type'], 'report_date_only')

    def test_multi_format_date_parsing(self):
        import pandas as pd
        from crime_data.utils import parse_date_series

        # Case A: DD/MM/YYYY (Day-first inferred from 25 > 12)
        s1 = pd.Series(['15/01/2024', '25/02/2024', '05/03/2024'])
        parsed1, inv1, _, fmt1, _ = parse_date_series(s1)
        self.assertEqual(len(inv1), 0)
        self.assertEqual(parsed1[0], date(2024, 1, 15))
        self.assertEqual(parsed1[1], date(2024, 2, 25))
        self.assertEqual(parsed1[2], date(2024, 3, 5))

        # Case B: MM/DD/YYYY (Month-first inferred from second token > 12)
        s2 = pd.Series(['01/15/2024', '02/25/2024', '03/05/2024'])
        parsed2, inv2, _, fmt2, _ = parse_date_series(s2)
        self.assertEqual(len(inv2), 0)
        self.assertEqual(parsed2[0], date(2024, 1, 15))
        self.assertEqual(parsed2[1], date(2024, 2, 25))

        # Case C: Excel numeric serials
        s3 = pd.Series([45427, 45428]) # 2024-05-15 and 2024-05-16
        parsed3, inv3, _, _, _ = parse_date_series(s3)
        self.assertEqual(len(inv3), 0)
        self.assertEqual(parsed3[0], date(2024, 5, 15))

    def test_optional_case_fields_detection(self):
        import pandas as pd
        from crime_data.utils import detect_column_mapping

        df = pd.DataFrame({
            'Crime Offense': ['Robbery'],
            'Place': ['Gandhi Chowk'],
            'Date': ['2024-06-01'],
            'Time of Occurrence': ['14:30'],
            'Crime Code': ['IPC-392'],
            'Victim Age': [35],
            'Victim Gender': ['Female'],
            'Weapon Used': ['Knife'],
        })

        mapping = detect_column_mapping(df)
        t2o = mapping['target_to_original']

        self.assertEqual(t2o.get('crime_category'), 'Crime Offense')
        self.assertEqual(t2o.get('location'), 'Place')
        self.assertEqual(t2o.get('incident_date'), 'Date')
        self.assertEqual(t2o.get('incident_time'), 'Time of Occurrence')
        self.assertEqual(t2o.get('crime_code'), 'Crime Code')
        self.assertEqual(t2o.get('victim_age'), 'Victim Age')
        self.assertEqual(t2o.get('victim_gender'), 'Victim Gender')
        self.assertEqual(t2o.get('weapon_used'), 'Weapon Used')


class TestPartialRowValidationAndIngestion(TestCase):
    def setUp(self):
        self.analyst = User.objects.create_user(
            username='qa_analyst',
            email='qa@example.com',
            password='Password123!',
            role='analyst'
        )

    def test_partial_valid_rows_ingested_and_invalid_skipped(self):
        import pandas as pd
        from crime_data.utils import process_dataset

        # 5 rows total: 3 valid, 1 invalid date, 1 empty category
        df = pd.DataFrame({
            'Crime Type': ['Assault', 'Burglary', 'Theft', 'Robbery', ''],
            'Location': ['North Zone', 'South Zone', 'East Zone', 'West Zone', 'Central Zone'],
            'Date of Occurrence': ['2024-07-01', '2024-07-02', 'invalid_date_xyz', '2024-07-04', '2024-07-05'],
        })

        upload = DatasetUpload.objects.create(
            user=self.analyst,
            original_filename='mixed_quality.csv',
            status='pending',
            total_records=5
        )

        process_dataset(upload, df)
        upload.refresh_from_db()

        # Ingestion must succeed for the valid rows!
        self.assertEqual(upload.status, 'completed')
        self.assertEqual(upload.valid_records, 3)
        self.assertEqual(upload.invalid_records, 2)
        self.assertEqual(CrimeRecord.objects.filter(dataset_upload=upload).count(), 3)

        # Explanations must be captured in validation_errors
        inv_details = upload.validation_errors.get('invalid_row_details', [])
        self.assertEqual(len(inv_details), 2)
        reasons_text = " ".join([d['issue'] for d in inv_details])
        self.assertIn("Invalid Date", reasons_text)
        self.assertIn("Crime Category", reasons_text)


