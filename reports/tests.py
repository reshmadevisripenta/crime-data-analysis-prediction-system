from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from crime_data.models import Location, CrimeCategory
from reports.models import Report, ReportExport


class TestReportModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reportuser',
            email='report@example.com',
            password='Password123!',
            role='analyst'
        )
        self.location = Location.objects.create(
            name='South Extension',
            city='Delhi',
            state='Delhi',
            latitude=28.5700,
            longitude=77.2200
        )
        self.category = CrimeCategory.objects.create(name='Robbery')

    def test_report_creation_with_all_fields(self):
        report = Report.objects.create(
            name='Annual Crime Report 2024',
            report_type='crime_analysis',
            description='Detailed annual breakdown',
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
            location=self.location,
            category=self.category,
            parameters={'filter': 'annual'},
            generated_by=self.user,
            status='generating'
        )
        self.assertEqual(report.name, 'Annual Crime Report 2024')
        self.assertEqual(report.report_type, 'crime_analysis')
        self.assertEqual(report.location, self.location)
        self.assertEqual(report.category, self.category)
        self.assertEqual(report.generated_by, self.user)
        self.assertEqual(report.status, 'generating')
        self.assertIn('Annual Crime Report 2024', str(report))

    def test_status_transitions(self):
        report = Report.objects.create(
            name='Weekly Summary',
            report_type='trend_report',
            generated_by=self.user,
            status='generating'
        )
        self.assertEqual(report.status, 'generating')

        report.status = 'ready'
        report.save()
        report.refresh_from_db()
        self.assertEqual(report.status, 'ready')

        report.status = 'failed'
        report.save()
        report.refresh_from_db()
        self.assertEqual(report.status, 'failed')


class TestReportExport(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='exportuser',
            email='export@example.com',
            password='Password123!',
            role='analyst'
        )
        self.report = Report.objects.create(
            name='Monthly Analysis',
            report_type='crime_analysis',
            generated_by=self.user,
            status='ready'
        )

    def test_report_export_creation(self):
        dummy_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 dummy pdf content", content_type="application/pdf")
        export = ReportExport.objects.create(
            report=self.report,
            export_format='pdf',
            file=dummy_file,
            file_size=1024
        )
        self.assertEqual(export.report, self.report)
        self.assertEqual(export.export_format, 'pdf')
        self.assertEqual(export.file_size, 1024)
        self.assertIn('Monthly Analysis (PDF)', str(export))


class TestReportView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewerreport',
            email='viewerreport@example.com',
            password='Password123!',
            role='viewer'
        )

    def test_reports_list_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:reports'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('reports_history', response.context)
        self.assertIn('report_types', response.context)
        self.assertIn('locations', response.context)
        self.assertIn('categories', response.context)
