from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer,
    PasswordConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
)
from .utils import (
    User,
    check_token,
    delete_auth_cookies,
    get_user_from_uidb64,
    make_token,
    send_activation_email,
    send_password_reset_email,
    set_access_cookie,
    set_auth_cookies,
)


class RegisterView(APIView):
    """Register a new (inactive) user and send an activation email."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = make_token(user)
        send_activation_email(user, token)
        return Response(
            {'user': {'id': user.id, 'email': user.email}, 'token': token},
            status=status.HTTP_201_CREATED,
        )


class ActivateView(APIView):
    """Activate a user account from the emailed uid/token link."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, uidb64, token):
        user = get_user_from_uidb64(uidb64)
        if user is None or not check_token(user, token):
            return Response(
                {'detail': 'Activation failed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'message': 'Account successfully activated.'})


class LoginView(APIView):
    """Authenticate a user and set JWT tokens as HttpOnly cookies."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        response = Response({
            'detail': 'Login successful',
            'user': {'id': user.id, 'username': user.email},
        })
        set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


class LogoutView(APIView):
    """Blacklist the refresh token and clear the auth cookies."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh = request.COOKIES.get('refresh_token')
        if not refresh:
            return Response(
                {'detail': 'Refresh token missing.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self._blacklist(refresh)
        response = Response({
            'detail': 'Logout successful! All tokens will be deleted. '
                      'Refresh token is now invalid.'
        })
        delete_auth_cookies(response)
        return response

    @staticmethod
    def _blacklist(refresh):
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            pass


class CookieTokenRefreshView(APIView):
    """Issue a new access token from the refresh token cookie."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh = request.COOKIES.get('refresh_token')
        if not refresh:
            return Response(
                {'detail': 'Refresh token missing.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._refresh(refresh)

    def _refresh(self, refresh):
        try:
            token = RefreshToken(refresh)
        except TokenError:
            return Response(
                {'detail': 'Invalid refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        access = str(token.access_token)
        response = Response({'detail': 'Token refreshed', 'access': access})
        set_access_cookie(response, access)
        return response


class PasswordResetView(APIView):
    """Send a password reset link if a matching active user exists."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._notify(serializer.validated_data['email'])
        return Response(
            {'detail': 'An email has been sent to reset your password.'}
        )

    @staticmethod
    def _notify(email):
        user = User.objects.filter(email=email, is_active=True).first()
        if user is not None:
            send_password_reset_email(user, make_token(user))


class PasswordConfirmView(APIView):
    """Set a new password using the emailed uid/token link."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_from_uidb64(uidb64)
        if user is None or not check_token(user, token):
            return Response(
                {'detail': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Your Password has been successfully reset.'})
