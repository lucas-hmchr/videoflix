from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

# Use the in-memory email backend so we can inspect sent activation mails.
TEST_EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


@override_settings(EMAIL_BACKEND=TEST_EMAIL_BACKEND)
class RegistrationFlowTests(TestCase):
    """End-to-end check of register -> activation email -> activate."""

    def setUp(self):
        self.client = APIClient()
        self.payload = {
            'email': 'newuser@example.com',
            'password': 'sup3rsecret!',
            'confirmed_password': 'sup3rsecret!',
        }

    def test_register_creates_inactive_user_and_sends_email(self):
        response = self.client.post(reverse('register'), self.payload, format='json')

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email=self.payload['email'])
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)

    def test_activation_link_uses_configured_frontend_url(self):
        self.client.post(reverse('register'), self.payload, format='json')

        body = mail.outbox[0].body
        # The link must point at the frontend's activation page (port 5500),
        # which itself calls the backend API via fetch().
        self.assertIn(settings.FRONTEND_URL, body)
        self.assertIn('http://localhost:5500/pages/auth/activate.html?uid=', body)

    @override_settings(FRONTEND_URL='http://localhost:5500')
    def test_full_flow_activate_then_login(self):
        # Register
        self.client.post(reverse('register'), self.payload, format='json')
        user = User.objects.get(email=self.payload['email'])

        # Pull uid/token out of the emailed frontend link's query string, the
        # same way the frontend's JS does, and hit the backend activate API.
        link = mail.outbox[0].body.split('http://localhost:5500', 1)[1].strip()
        self.assertTrue(link.startswith('/pages/auth/activate.html?'))
        query = parse_qs(urlsplit(link).query)
        uid, token = query['uid'][0], query['token'][0]
        response = self.client.get(reverse('activate', args=[uid, token]))
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # Now login succeeds for the activated account.
        login = self.client.post(
            reverse('login'),
            {'email': self.payload['email'], 'password': self.payload['password']},
            format='json',
        )
        self.assertEqual(login.status_code, 200)
