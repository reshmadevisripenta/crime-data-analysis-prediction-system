from django.db import models
from django.conf import settings
from model_training.models import MLModel
from crime_data.models import Location, CrimeCategory


class PredictionResult(models.Model):
    FORECAST_PERIOD_CHOICES = [
        ('1_month', '1 Month'),
        ('3_months', '3 Months'),
        ('6_months', '6 Months'),
        ('1_year', '1 Year'),
    ]

    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='predictions')
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prediction_results'
    )
    category = models.ForeignKey(
        CrimeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prediction_results'
    )
    forecast_period = models.CharField(max_length=20, choices=FORECAST_PERIOD_CHOICES, default='1_month')
    predicted_count = models.FloatField(help_text='Predicted total crime count for the period')
    lower_bound = models.FloatField(null=True, blank=True, help_text='Lower confidence bound')
    upper_bound = models.FloatField(null=True, blank=True, help_text='Upper confidence bound')
    confidence_level = models.FloatField(default=0.95, help_text='Confidence level percentage, default 0.95 (95%)')
    actual_count = models.IntegerField(null=True, blank=True, help_text='Actual observed count filled later for verification')
    prediction_date = models.DateField(auto_now_add=True)
    prediction_data = models.JSONField(default=dict, blank=True, help_text='Full forecast chart series data, monthly breakdowns, features')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='predictions')

    class Meta:
        verbose_name = 'Prediction Result'
        verbose_name_plural = 'Prediction Results'
        ordering = ['-prediction_date', '-id']

    def __str__(self):
        cat_str = self.category.name if self.category else "All Categories"
        loc_str = self.location.name if self.location else "All Locations"
        return f'Prediction: {cat_str} in {loc_str} ({self.get_forecast_period_display()}) = {self.predicted_count:.1f}'
