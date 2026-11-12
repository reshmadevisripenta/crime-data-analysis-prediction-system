from django.db import models
from django.conf import settings
from crime_data.models import DatasetUpload


class MLModel(models.Model):
    ALGORITHM_CHOICES = [
        ('random_forest', 'Random Forest Regressor'),
        ('gradient_boosting', 'Gradient Boosting Regressor'),
        ('linear_regression', 'Linear Regression'),
        ('decision_tree', 'Decision Tree Regressor'),
        ('ridge', 'Ridge Regression'),
        ('svr', 'Support Vector Regressor'),
    ]

    STATUS_CHOICES = [
        ('training', 'Training'),
        ('trained', 'Trained'),
        ('failed', 'Failed'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=150)
    algorithm = models.CharField(max_length=50, choices=ALGORITHM_CHOICES)
    version = models.CharField(max_length=50, default='v1.0')
    dataset = models.ForeignKey(DatasetUpload, on_delete=models.SET_NULL, null=True, blank=True, related_name='trained_models')
    target_variable = models.CharField(max_length=100, default='crime_count')
    features = models.JSONField(default=list, help_text='List of feature names used for training')
    hyperparameters = models.JSONField(default=dict, blank=True, help_text='Hyperparameters configuration')
    model_file = models.FileField(upload_to='trained_models/', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='training')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ml_models')
    created_at = models.DateTimeField(auto_now_add=True)
    trained_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'ML Model'
        verbose_name_plural = 'ML Models'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_algorithm_display()} - {self.version})'


class ModelEvaluation(models.Model):
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='evaluations')
    mae = models.FloatField(verbose_name='Mean Absolute Error')
    mse = models.FloatField(verbose_name='Mean Squared Error')
    rmse = models.FloatField(verbose_name='Root Mean Squared Error')
    r2_score = models.FloatField(verbose_name='R² Score')
    accuracy = models.FloatField(null=True, blank=True, verbose_name='Accuracy (%)')
    training_samples = models.IntegerField(default=0)
    test_samples = models.IntegerField(default=0)
    evaluation_notes = models.TextField(blank=True)
    baseline_mae = models.FloatField(default=0.0, verbose_name='Baseline MAE')
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Model Evaluation'
        verbose_name_plural = 'Model Evaluations'
        ordering = ['-evaluated_at']

    def __str__(self):
        return f'Evaluation for {self.model.name} (R²: {self.r2_score:.4f}, RMSE: {self.rmse:.4f})'
