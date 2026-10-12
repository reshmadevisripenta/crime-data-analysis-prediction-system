from django.db import models
from django.conf import settings
from crime_data.models import Location, CrimeCategory


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('crime_analysis', 'Crime Analysis Report'),
        ('location_summary', 'Location Summary Report'),
        ('category_report', 'Category Report'),
        ('trend_report', 'Trend Report'),
        ('prediction_report', 'Prediction Report'),
    ]

    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )
    category = models.ForeignKey(
        CrimeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )
    parameters = models.JSONField(default=dict, blank=True, help_text='Report filter parameters and configurations')
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_report_type_display()} - {self.get_status_display()})'


class ReportExport(models.Model):
    EXPORT_FORMAT_CHOICES = [
        ('pdf', 'PDF Document'),
        ('csv', 'CSV Spreadsheet'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='exports')
    export_format = models.CharField(max_length=10, choices=EXPORT_FORMAT_CHOICES, default='pdf')
    file = models.FileField(upload_to='reports/')
    file_size = models.IntegerField(null=True, blank=True, help_text='File size in bytes')
    exported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Report Export'
        verbose_name_plural = 'Report Exports'
        ordering = ['-exported_at']

    def __str__(self):
        return f'{self.report.name} ({self.export_format.upper()})'
