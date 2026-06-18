from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()


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


def send_activation_email(user, token):
    """Send the account activation link to the user via email."""
    link = f"{settings.FRONTEND_URL}/api/activate/{encode_uid(user)}/{token}/"
    send_mail(
        subject='Activate your Videoflix account',
        message=f'Please activate your account: {link}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def send_password_reset_email(user, token):
    """Send the password reset link to the user via email."""
    link = f"{settings.FRONTEND_URL}/api/password_confirm/{encode_uid(user)}/{token}/"
    send_mail(
        subject='Reset your Videoflix password',
        message=f'Reset your password here: {link}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
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
