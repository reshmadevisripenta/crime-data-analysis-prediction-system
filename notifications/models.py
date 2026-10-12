from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('success', 'Success'),
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    CATEGORY_CHOICES = [
        ('upload', 'Dataset Upload'),
        ('analysis', 'Analysis'),
        ('training', 'Model Training'),
        ('prediction', 'Prediction'),
        ('report', 'Report Generation'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='info')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='system')
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=255, null=True, blank=True, help_text='Link to relevant page/resource')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.user.username} ({self.get_notification_type_display()})'

    @classmethod
    def create_notification(cls, user, title, message, notif_type, category, action_url=None):
        """Helper method to create and persist a notification."""
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notif_type,
            category=category,
            action_url=action_url
        )
