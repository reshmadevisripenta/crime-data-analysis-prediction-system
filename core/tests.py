from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import AuditLog, ContactMessage

User = get_user_model()


class AuditLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='officer1',
            email='officer1@example.com',
            password='Password123!',
            role='analyst'
        )

    def test_audit_log_creation(self):
        log = AuditLog.objects.create(
            user=self.user,
            action='upload',
            resource_type='CrimeDataset',
            resource_id=1,
            details={'filename': 'jan_2024.csv'},
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0'
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'upload')
        self.assertEqual(log.resource_type, 'CrimeDataset')
        self.assertIn('officer1', str(log))
        self.assertIn('Dataset Upload', str(log))

    def test_audit_log_anonymous(self):
        log = AuditLog.objects.create(
            user=None,
            action='page_view',
            resource_type='Home',
            ip_address='192.168.1.1'
        )
        self.assertIn('Anonymous', str(log))
        self.assertIn('Page View', str(log))


class CoreViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='Password123!',
            role='admin'
        )
        self.analyst_user = User.objects.create_user(
            username='analystuser',
            email='analyst@example.com',
            password='Password123!',
            role='analyst'
        )
        self.viewer_user = User.objects.create_user(
            username='vieweruser',
            email='viewer@example.com',
            password='Password123!',
            role='viewer'
        )

    def test_home_view(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_api_docs_view_unauthenticated(self):
        response = self.client.get(reverse('core:api_docs'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_api_docs_view_authenticated(self):
        self.client.force_login(self.analyst_user)
        response = self.client.get(reverse('core:api_docs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'API Reference')
        self.assertContains(response, '/crime-data/records/')
        self.assertContains(response, '/analysis/api/data/')

    def test_audit_log_view_unauthenticated(self):
        response = self.client.get(reverse('core:audit_log'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_audit_log_view_non_admin_forbidden(self):
        self.client.force_login(self.analyst_user)
        response = self.client.get(reverse('core:audit_log'))
        self.assertEqual(response.status_code, 403)

    def test_audit_log_view_admin_success(self):
        AuditLog.objects.create(
            user=self.admin_user,
            action='login',
            resource_type='Authentication',
            ip_address='127.0.0.1'
        )
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('core:audit_log'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'System Activity Audit Log')
        self.assertContains(response, 'adminuser')
        self.assertContains(response, 'User Login')

    def test_audit_log_filter_by_action(self):
        AuditLog.objects.create(user=self.admin_user, action='login', ip_address='127.0.0.1')
        AuditLog.objects.create(user=self.admin_user, action='upload', ip_address='127.0.0.1')
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('core:audit_log') + '?action=upload')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dataset Upload')


class AuditMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testperson',
            email='testperson@example.com',
            password='SecretPassword123!',
            role='analyst'
        )

    def test_login_post_creates_audit_log(self):
        initial_count = AuditLog.objects.filter(action='login').count()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testperson',
            'password': 'SecretPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        after_count = AuditLog.objects.filter(action='login').count()
        self.assertEqual(after_count, initial_count + 1)
