"""
accounts/models.py — Custom User model for the Crime Data Analysis Prediction System.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model with role-based access control and profile fields.
    """

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('analyst', 'Analyst'),
        ('viewer', 'Viewer'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    phone = models.CharField(max_length=20, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    def is_admin(self):
        """Check if user has admin-level access."""
        return self.role == 'admin' or self.is_superuser

    def is_analyst(self):
        """Check if user has analyst-level access or higher."""
        return self.role in ['admin', 'analyst'] or self.is_superuser

    def get_initials(self):
        """Return initials from full name or username."""
        if self.first_name and self.last_name:
            return f'{self.first_name[0]}{self.last_name[0]}'.upper()
        return self.username[:2].upper()

    def get_full_name(self):
        full = super().get_full_name()
        return full if full else self.username
