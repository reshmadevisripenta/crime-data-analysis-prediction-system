import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from crime_data.models import DatasetUpload
from model_training.models import MLModel
from reports.models import Report
from .models import Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DatasetUpload)
def notify_dataset_upload_completion(sender, instance, created, **kwargs):
    """
    Sends notification when a dataset upload finishes processing or fails.
    """
    if created:
        return

    # Trigger only when status transitioned to terminal states
    if instance.status == 'completed':
        Notification.objects.get_or_create(
            user=instance.user,
            title="Dataset Ingestion Completed",
            message=f"Dataset '{instance.original_filename}' has been fully ingested. {instance.valid_records} crime records added.",
            category='upload',
            defaults={
                'notification_type': 'success',
                'action_url': f'/crime-data/preview/{instance.id}/'
            }
        )
    elif instance.status == 'failed':
        Notification.objects.get_or_create(
            user=instance.user,
            title="Dataset Processing Failed",
            message=f"Dataset '{instance.original_filename}' failed processing. Review error logs.",
            category='upload',
            defaults={
                'notification_type': 'error',
                'action_url': '/crime-data/upload/'
            }
        )


@receiver(post_save, sender=MLModel)
def notify_ml_model_completion(sender, instance, created, **kwargs):
    """
    Sends notification when an MLModel finishes training.
    """
    if created:
        return

    if instance.status == 'trained':
        Notification.objects.get_or_create(
            user=instance.created_by,
            title="ML Model Ready",
            message=f"Model '{instance.name}' ({instance.get_algorithm_display()}) is trained and ready for crime prediction.",
            category='training',
            defaults={
                'notification_type': 'success',
                'action_url': f'/model-training/models/{instance.id}/'
            }
        )
    elif instance.status == 'failed':
        Notification.objects.get_or_create(
            user=instance.created_by,
            title="Model Training Failed",
            message=f"Model training for '{instance.name}' could not complete successfully.",
            category='training',
            defaults={
                'notification_type': 'error',
                'action_url': '/model-training/'
            }
        )


@receiver(post_save, sender=Report)
def notify_report_ready(sender, instance, created, **kwargs):
    """
    Sends notification when a Report compilation is marked ready.
    """
    if created:
        return

    if instance.status == 'ready':
        Notification.objects.get_or_create(
            user=instance.generated_by,
            title="Crime Analysis Report Generated",
            message=f"Report '{instance.name}' has been compiled and is ready for PDF/CSV download.",
            category='report',
            defaults={
                'notification_type': 'info',
                'action_url': '/reports/'
            }
        )
