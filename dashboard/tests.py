from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from crime_data.models import CrimeCategory, Location, CrimeRecord


class TestDashboardView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='dashuser',
            email='dash@example.com',
            password='Password123!',
            role='analyst'
        )
        self.category = CrimeCategory.objects.create(name='Robbery')
        self.location = Location.objects.create(
            name='Central Mall',
            city='Delhi',
            state='Delhi',
            latitude=28.6139,
            longitude=77.2090
        )
        CrimeRecord.objects.create(
            category=self.category,
            location=self.location,
            incident_date=date.today(),
            description='Test robbery incident',
            severity='high',
            status='reported'
        )

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    def test_authenticated_access_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_context_contains_kpi_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

        self.assertIn('total_crime_records', response.context)
        self.assertIn('total_categories', response.context)
        self.assertIn('total_locations', response.context)
        self.assertIn('total_predictions', response.context)

        self.assertEqual(response.context['total_crime_records'], 1)
        self.assertEqual(response.context['total_categories'], 1)
        self.assertEqual(response.context['total_locations'], 1)
