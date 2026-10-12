from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User


class TestUserModel(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='Password123!',
            role='admin',
            first_name='John',
            last_name='Doe'
        )
        self.analyst_user = User.objects.create_user(
            username='analystuser',
            email='analyst@example.com',
            password='Password123!',
            role='analyst',
            first_name='Jane',
            last_name='Smith'
        )
        self.viewer_user = User.objects.create_user(
            username='vieweruser',
            email='viewer@example.com',
            password='Password123!',
            role='viewer'
        )

    def test_user_creation(self):
        self.assertEqual(self.admin_user.username, 'adminuser')
        self.assertEqual(self.admin_user.role, 'admin')
        self.assertEqual(self.viewer_user.role, 'viewer')
        self.assertTrue(self.admin_user.is_active)

    def test_role_checks(self):
        self.assertTrue(self.admin_user.is_admin())
        self.assertTrue(self.admin_user.is_analyst())

        self.assertFalse(self.analyst_user.is_admin())
        self.assertTrue(self.analyst_user.is_analyst())

        self.assertFalse(self.viewer_user.is_admin())
        self.assertFalse(self.viewer_user.is_analyst())

    def test_get_initials(self):
        self.assertEqual(self.admin_user.get_initials(), 'JD')
        self.assertEqual(self.analyst_user.get_initials(), 'JS')
        self.assertEqual(self.viewer_user.get_initials(), 'VI')

    def test_string_representation(self):
        self.assertEqual(str(self.admin_user), 'adminuser (Administrator)')
        self.assertEqual(str(self.analyst_user), 'analystuser (Analyst)')
        self.assertEqual(str(self.viewer_user), 'vieweruser (Viewer)')


class TestLoginView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testlogin',
            email='login@example.com',
            password='SecretPassword123!',
            role='viewer'
        )

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testlogin',
            'password': 'SecretPassword123!'
        })
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_invalid_login_shows_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testlogin',
            'password': 'WrongPassword!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid credentials')

    def test_unauthenticated_access_to_profile_redirects_to_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))


class TestRegisterView(TestCase):
    def setUp(self):
        self.client = Client()
        self.existing_user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='Password123!'
        )

    def test_valid_registration_creates_user_and_redirects_to_login(self):
        response = self.client.post(reverse('accounts:register'), {
            'full_name': 'New User',
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_duplicate_username_fails(self):
        response = self.client.post(reverse('accounts:register'), {
            'full_name': 'Another User',
            'username': 'existinguser',
            'email': 'different@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'username', 'This username is already taken.')

    def test_duplicate_email_fails(self):
        response = self.client.post(reverse('accounts:register'), {
            'full_name': 'Another User',
            'username': 'uniqueuser',
            'email': 'existing@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'A user with this email address already exists.')

    def test_password_mismatch_fails(self):
        response = self.client.post(reverse('accounts:register'), {
            'full_name': 'Mismatch User',
            'username': 'mismatchuser',
            'email': 'mismatch@example.com',
            'password1': 'Password123!',
            'password2': 'Password456!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'password2', 'Passwords do not match.')

    def test_registration_with_first_and_last_name(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'Jane',
            'last_name': 'Investigator',
            'username': 'jane_inv',
            'email': 'jane.inv@example.com',
            'role': 'analyst',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        self.assertRedirects(response, reverse('accounts:login'))
        user = User.objects.get(username='jane_inv')
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Investigator')
        self.assertEqual(user.role, 'analyst')
        self.assertTrue(user.check_password('StrongPass123!'))


class TestProfileView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='Password123!',
            first_name='Original',
            last_name='Name',
            phone='1234567890',
            organization='Original Org',
            bio='Original Bio'
        )
        self.client.force_login(self.user)

    def test_authenticated_user_sees_profile_form(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'profileuser')
        self.assertIn('form', response.context)

    def test_profile_update_saves_data(self):
        response = self.client.post(reverse('accounts:profile'), {
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'updated@example.com',
            'phone': '9876543210',
            'organization': 'Updated Police Dept',
            'bio': 'Updated investigator bio'
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.phone, '9876543210')
        self.assertEqual(self.user.organization, 'Updated Police Dept')
        self.assertEqual(self.user.bio, 'Updated investigator bio')


class TestLogoutView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='logoutuser',
            email='logout@example.com',
            password='Password123!'
        )
        self.client.force_login(self.user)

    def test_post_logout_clears_session_and_redirects(self):
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
        # Check session is cleared / user is anonymous
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
