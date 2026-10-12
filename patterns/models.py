from django.db import models
from django.conf import settings
from crime_data.models import DatasetUpload


class CrimePattern(models.Model):
    PATTERN_TYPE_CHOICES = [
        ('temporal', 'Temporal Pattern'),
        ('geographic', 'Geographic Pattern'),
        ('category', 'Category Correlation'),
        ('seasonal', 'Seasonal Pattern'),
    ]

    name = models.CharField(max_length=200)
    pattern_type = models.CharField(max_length=30, choices=PATTERN_TYPE_CHOICES)
    description = models.TextField()
    dataset = models.ForeignKey(
        DatasetUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crime_patterns'
    )
    pattern_data = models.JSONField(default=dict, blank=True, help_text='Cluster coordinates, recurring time windows, correlation matrices')
    statistical_significance = models.FloatField(null=True, blank=True, help_text='p-value, correlation coefficient, or confidence level')
    observations = models.TextField(blank=True, help_text='Detailed analytical findings and observations')
    identified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='identified_patterns')
    identified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Crime Pattern'
        verbose_name_plural = 'Crime Patterns'
        ordering = ['-identified_at']

    def __str__(self):
        return f'{self.name} ({self.get_pattern_type_display()})'
