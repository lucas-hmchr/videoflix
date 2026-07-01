import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()
logger = logging.getLogger(__name__)
LOGO_PATH = settings.BASE_DIR / 'templates' / 'emails' / 'logo.png'


def encode_uid(user):
    """Return the URL-safe base64 encoded primary key of a user."""
    return urlsafe_base64_encode(force_bytes(user.pk))


def get_user_from_uidb64(uidb64):
    """Decode a uidb64 value and return the matching user or None."""
    try:
        pk = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=pk)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def make_token(user):
    """Create a signed, single-use token for the given user."""
    return default_token_generator.make_token(user)


def check_token(user, token):
    """Validate a token previously issued for the user."""
    return default_token_generator.check_token(user, token)


class _InlineLogoEmail(EmailMultiAlternatives):
    """Multipart email that embeds the Videoflix logo inline as cid:logo."""

    def _add_attachments(self, msg):
        """Attach the logo to the HTML part so it becomes multipart/related."""
        html_part = msg.get_payload()[-1]
        with open(LOGO_PATH, 'rb') as logo_file:
            html_part.add_related(
                logo_file.read(), maintype='image', subtype='png',
                cid='<logo>', disposition='inline', filename='logo.png',
            )


def _send_html_email(subject, template, context, recipient, text_body):
    """Render an HTML template and send it as a multipart (text + HTML) email."""
    html_body = render_to_string(template, context)
    email = _InlineLogoEmail(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    email.attach_alternative(html_body, 'text/html')
    email.send()


def send_activation_email(user, token):
    """Send the account activation link to the user via email."""
    link = f"{settings.FRONTEND_URL}/pages/auth/activate.html?uid={encode_uid(user)}&token={token}"
    logger.info('Activation link for %s: %s', user.email, link)
    _send_html_email(
        'Activate your Videoflix account', 'emails/activation_email.html',
        {'user_email': user.email, 'activation_link': link},
        user.email, f'Please activate your account: {link}',
    )


def send_password_reset_email(user, token):
    """Send the password reset link to the user via email."""
    link = f"{settings.FRONTEND_URL}/pages/auth/confirm_password.html?uid={encode_uid(user)}&token={token}"
    logger.info('Password reset link for %s: %s', user.email, link)
    _send_html_email(
        'Reset your Videoflix password', 'emails/password_reset_email.html',
        {'user_email': user.email, 'reset_link': link},
        user.email, f'Reset your password here: {link}',
    )


def set_access_cookie(response, access):
    """Attach only the access token as an HttpOnly cookie to a response."""
    response.set_cookie(
        'access_token', access,
        httponly=True, secure=not settings.DEBUG, samesite='Lax',
    )


def set_auth_cookies(response, access, refresh):
    """Attach access and refresh tokens as HttpOnly cookies to a response."""
    set_access_cookie(response, access)
    response.set_cookie(
        'refresh_token', refresh,
        httponly=True, secure=not settings.DEBUG, samesite='Lax',
    )


def delete_auth_cookies(response):
    """Remove the access and refresh token cookies from a response."""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
