from django.db import models
from django.conf import settings


class CrimeCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color_code = models.CharField(max_length=7, default='#FF5733', help_text='Hex color code e.g. #FF5733')
    icon = models.CharField(max_length=50, blank=True, default='bi-shield-exclamation', help_text='Bootstrap icon class name')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Crime Category'
        verbose_name_plural = 'Crime Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Location(models.Model):
    REGION_CHOICES = [
        ('urban', 'Urban'),
        ('suburban', 'Suburban'),
        ('rural', 'Rural'),
    ]

    name = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    region_type = models.CharField(max_length=20, choices=REGION_CHOICES, default='urban')
    population = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['city', 'name']

    def __str__(self):
        return f'{self.name}, {self.city}, {self.state}'


class DatasetUpload(models.Model):
    FILE_TYPE_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dataset_uploads')
    file = models.FileField(upload_to='datasets/')
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='csv')
    total_records = models.IntegerField(default=0)
    valid_records = models.IntegerField(default=0)
    invalid_records = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    validation_errors = models.JSONField(default=dict, blank=True)
    processing_notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Dataset Upload'
        verbose_name_plural = 'Dataset Uploads'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.original_filename} ({self.get_status_display()})'


class CrimeRecord(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('under_investigation', 'Under Investigation'),
        ('solved', 'Solved'),
        ('closed', 'Closed'),
    ]

    category = models.ForeignKey(CrimeCategory, on_delete=models.CASCADE, related_name='crime_records')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='crime_records')
    incident_date = models.DateField()
    incident_time = models.TimeField(null=True, blank=True)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='reported')
    source = models.CharField(max_length=200, blank=True, help_text='Source of the crime record')
    dataset_upload = models.ForeignKey(
        DatasetUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crime_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Crime Record'
        verbose_name_plural = 'Crime Records'
        ordering = ['-incident_date', '-created_at']

    def __str__(self):
        return f'{self.category.name} at {self.location.name} on {self.incident_date}'
