from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from crime_data.models import CrimeCategory, Location, DatasetUpload
from model_training.models import MLModel
from prediction.models import PredictionResult


class TestPredictionModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='preduser',
            email='pred@example.com',
            password='Password123!',
            role='analyst'
        )
        self.dataset = DatasetUpload.objects.create(
            user=self.user,
            original_filename='crimes.csv',
            status='completed'
        )
        self.ml_model = MLModel.objects.create(
            name='Random Forest Regressor v1',
            algorithm='random_forest',
            dataset=self.dataset,
            created_by=self.user,
            status='trained'
        )
        self.category = CrimeCategory.objects.create(name='Assault')
        self.location = Location.objects.create(
            name='Sector 18',
            city='Noida',
            state='Uttar Pradesh',
            latitude=28.5700,
            longitude=77.3200
        )

    def test_prediction_result_creation_with_all_fields(self):
        pred = PredictionResult.objects.create(
            model=self.ml_model,
            location=self.location,
            category=self.category,
            forecast_period='3_months',
            predicted_count=45.5,
            lower_bound=38.0,
            upper_bound=53.0,
            confidence_level=0.95,
            actual_count=42,
            prediction_data={'trend': [15.0, 15.2, 15.3]},
            requested_by=self.user
        )
        self.assertEqual(pred.model, self.ml_model)
        self.assertEqual(pred.location, self.location)
        self.assertEqual(pred.category, self.category)
        self.assertEqual(pred.forecast_period, '3_months')
        self.assertEqual(pred.predicted_count, 45.5)
        self.assertEqual(pred.lower_bound, 38.0)
        self.assertEqual(pred.upper_bound, 53.0)
        self.assertEqual(pred.confidence_level, 0.95)
        self.assertEqual(pred.actual_count, 42)
        self.assertEqual(pred.requested_by, self.user)
        self.assertIn('Prediction: Assault in Sector 18', str(pred))


class TestPredictionView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewerpred',
            email='viewerpred@example.com',
            password='Password123!',
            role='viewer'
        )

    def test_page_loads_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('prediction:prediction'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('models', response.context)
        self.assertIn('locations', response.context)
        self.assertIn('categories', response.context)
        self.assertIn('past_predictions', response.context)
