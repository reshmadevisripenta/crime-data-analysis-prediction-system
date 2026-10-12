import json
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from crime_data.models import CrimeCategory, Location, CrimeRecord
from analysis.models import AnalysisResult, TrendData


class TestAnalysisView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='analyst1',
            email='analyst1@example.com',
            password='Password123!',
            role='analyst'
        )
        self.category = CrimeCategory.objects.create(name='Theft')
        self.location = Location.objects.create(
            name='Station Road',
            city='Pune',
            state='Maharashtra',
            latitude=18.5204,
            longitude=73.8567
        )
        CrimeRecord.objects.create(
            category=self.category,
            location=self.location,
            incident_date=date.today(),
            description='Bag snatching incident',
            severity='medium'
        )

    def test_page_loads_with_chart_data_in_context(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('analysis:analysis'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('category_freq_json', response.context)
        self.assertIn('monthly_trends_json', response.context)
        self.assertIn('yearly_trends_json', response.context)
        self.assertIn('categories', response.context)
        self.assertIn('locations', response.context)


class TestAnalysisDataAPI(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='analyst2',
            email='analyst2@example.com',
            password='Password123!',
            role='analyst'
        )
        self.category = CrimeCategory.objects.create(name='Burglary')
        self.location = Location.objects.create(
            name='Market Yard',
            city='Pune',
            state='Maharashtra',
            latitude=18.4900,
            longitude=73.8600
        )
        CrimeRecord.objects.create(
            category=self.category,
            location=self.location,
            incident_date=date(2024, 3, 15),
            description='House break-in'
        )

    def test_json_endpoint_returns_proper_structure(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('analysis:get_data'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('category_freq', data)
        self.assertIn('monthly_trends', data)
        self.assertIn('yearly_trends', data)
        self.assertIn('findings', data)
        self.assertIn('total_records', data)


class TestRunAnalysis(TestCase):
    def setUp(self):
        self.client = Client()
        self.analyst = User.objects.create_user(
            username='leadanalyst',
            email='lead@example.com',
            password='Password123!',
            role='analyst'
        )
        self.category = CrimeCategory.objects.create(name='Cyber Crime')
        self.location = Location.objects.create(
            name='Tech Park',
            city='Bengaluru',
            state='Karnataka',
            latitude=12.9716,
            longitude=77.5946
        )
        CrimeRecord.objects.create(
            category=self.category,
            location=self.location,
            incident_date=date(2024, 4, 1),
            description='Phishing attack reported'
        )

    def test_post_creates_analysis_result(self):
        self.client.force_login(self.analyst)
        response = self.client.post(reverse('analysis:run_analysis'), {
            'name': 'Q1 Cyber Crime Analysis',
            'analysis_type': 'frequency'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')

        analysis = AnalysisResult.objects.filter(name='Q1 Cyber Crime Analysis').first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.created_by, self.analyst)
        self.assertEqual(analysis.analysis_type, 'frequency')
        self.assertTrue(TrendData.objects.filter(analysis=analysis).exists())
