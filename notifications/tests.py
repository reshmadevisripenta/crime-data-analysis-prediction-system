from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from notifications.models import Notification


class TestNotificationModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notifuser',
            email='notif@example.com',
            password='Password123!',
            role='viewer'
        )

    def test_creation(self):
        notif = Notification.objects.create(
            user=self.user,
            title='System Alert',
            message='System maintenance scheduled',
            notification_type='warning',
            category='system'
        )
        self.assertEqual(notif.user, self.user)
        self.assertEqual(notif.title, 'System Alert')
        self.assertEqual(notif.notification_type, 'warning')
        self.assertFalse(notif.is_read)
        self.assertIn('System Alert', str(notif))

    def test_create_notification_classmethod(self):
        notif = Notification.create_notification(
            user=self.user,
            title='Analysis Complete',
            message='Trend analysis is ready',
            notif_type='success',
            category='analysis',
            action_url='/analysis/'
        )
        self.assertEqual(notif.user, self.user)
        self.assertEqual(notif.title, 'Analysis Complete')
        self.assertEqual(notif.notification_type, 'success')
        self.assertEqual(notif.action_url, '/analysis/')

    def test_mark_as_read(self):
        notif = Notification.objects.create(
            user=self.user,
            title='New Message',
            message='You have an update'
        )
        self.assertFalse(notif.is_read)
        notif.is_read = True
        notif.save()
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)


class TestNotificationView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewernotif',
            email='viewernotif@example.com',
            password='Password123!',
            role='viewer'
        )
        # Create 2 unread notifications and 1 read notification
        Notification.objects.create(
            user=self.user,
            title='Alert 1',
            message='Test message 1',
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title='Alert 2',
            message='Test message 2',
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title='Alert 3',
            message='Test message 3',
            is_read=True
        )

    def test_notification_list_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('notifications:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('notifications', response.context)
        self.assertIn('unread_count', response.context)
        self.assertEqual(len(response.context['notifications']), 3)

    def test_badge_count(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('notifications:get_unread_count'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('count'), 2)
