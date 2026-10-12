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
