from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Validates registration input and creates an inactive user."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirmed_password']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'}
            )
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({'email': 'Email already exists.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirmed_password')
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False,
        )


class LoginSerializer(serializers.Serializer):
    """Validates credentials and ensures the account is active."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if user is None:
            raise AuthenticationFailed('Invalid email or password.')
        if not user.is_active:
            raise AuthenticationFailed('Account is not activated.')
        attrs['user'] = user
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """Validates the email for a password reset request."""

    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    """Validates the new password and its confirmation."""

    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        return attrs
