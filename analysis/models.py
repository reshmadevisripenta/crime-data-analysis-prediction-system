from django.db import models
from django.conf import settings
from crime_data.models import DatasetUpload, Location, CrimeCategory


class AnalysisResult(models.Model):
    ANALYSIS_TYPE_CHOICES = [
        ('frequency', 'Frequency Analysis'),
        ('trend', 'Trend Analysis'),
        ('comparison', 'Comparison Analysis'),
        ('pattern', 'Pattern Analysis'),
    ]

    name = models.CharField(max_length=200)
    analysis_type = models.CharField(max_length=30, choices=ANALYSIS_TYPE_CHOICES)
    dataset = models.ForeignKey(
        DatasetUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analysis_results'
    )
    parameters = models.JSONField(default=dict, blank=True, help_text='Input parameters, filters, and configuration')
    results = models.JSONField(default=dict, blank=True, help_text='Stores chart data, statistical outputs, metrics')
    summary = models.TextField(blank=True, help_text='Human-readable summary of analysis insights')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analysis_results')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Analysis Result'
        verbose_name_plural = 'Analysis Results'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_analysis_type_display()})'


class TrendData(models.Model):
    PERIOD_TYPE_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='trend_data_points')
    period = models.CharField(max_length=30, help_text="e.g. '2023-01', '2023', '2023-W12'")
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trend_records'
    )
    category = models.ForeignKey(
        CrimeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trend_records'
    )
    crime_count = models.IntegerField(default=0)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES, default='monthly')

    class Meta:
        verbose_name = 'Trend Data'
        verbose_name_plural = 'Trend Data'
        ordering = ['period', '-crime_count']

    def __str__(self):
        cat_str = self.category.name if self.category else "All Categories"
        loc_str = self.location.name if self.location else "All Locations"
        return f'{self.period} - {cat_str} in {loc_str}: {self.crime_count}'
