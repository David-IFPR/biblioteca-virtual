import re
import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import PasswordResetToken, StudentProfile, User
from apps.accounts.validators import normalize_enrollment, validate_enrollment


def profile_of(user):
    try:
        return user.student_profile
    except StudentProfile.DoesNotExist:
        return None


class UserSerializer(serializers.ModelSerializer):
    enrollment = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "role", "enrollment", "is_blocked"]

    def get_enrollment(self, obj):
        profile = profile_of(obj)
        return profile.enrollment if profile else None

    def get_is_blocked(self, obj):
        profile = profile_of(obj)
        return bool(profile and profile.is_blocked)


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=180)
    enrollment = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_full_name(self, value):
        cleaned = " ".join(value.split())
        if len(cleaned) < 5 or " " not in cleaned:
            raise serializers.ValidationError("Informe o nome e o sobrenome.")
        return cleaned

    def validate_enrollment(self, value):
        try:
            normalized = validate_enrollment(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0]) from exc
        if StudentProfile.objects.filter(enrollment=normalized).exists():
            raise serializers.ValidationError("Já existe um cadastro com esta matrícula.")
        return normalized

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Já existe um cadastro com este e-mail.")
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "A confirmação de senha não confere."}
            )
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        enrollment = validated_data["enrollment"]
        with transaction.atomic():
            user = User(
                username=f"aluno-{enrollment}",
                email=validated_data["email"],
                full_name=validated_data["full_name"],
                role=User.Role.STUDENT,
                first_name=validated_data["full_name"].split()[0],
                last_name=" ".join(validated_data["full_name"].split()[1:]),
            )
            user.set_password(validated_data["password"])
            user.save()
            StudentProfile.objects.create(user=user, enrollment=enrollment)
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "A senha atual está incorreta."})
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "A confirmação de senha não confere."}
            )
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    enrollment = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        enrollment = normalize_enrollment(attrs.get("enrollment", ""))
        email = (attrs.get("email") or "").strip().lower()
        if not enrollment and not email:
            raise serializers.ValidationError("Informe a matrícula ou o e-mail.")
        attrs["enrollment"] = enrollment
        attrs["email"] = email
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "A confirmação de senha não confere."}
            )
        try:
            token = PasswordResetToken.objects.select_related("user").get(token=attrs["token"])
        except PasswordResetToken.DoesNotExist as exc:
            raise serializers.ValidationError({"token": "Token inválido ou expirado."}) from exc
        if not token.is_valid:
            raise serializers.ValidationError({"token": "Token inválido ou expirado."})
        try:
            validate_password(attrs["password"], token.user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        attrs["reset"] = token
        return attrs


def issue_reset(user):
    token = PasswordResetToken.issue(user)
    link = f"{settings.FRONTEND_URL.rstrip('/')}/redefinir-senha?token={token.token}"
    send_mail(
        subject="Redefinição de senha — Acervo",
        message=(
            f"Olá, {user.full_name}.\n\n"
            "Recebemos um pedido para redefinir a senha da biblioteca virtual.\n"
            f"Acesse: {link}\n\n"
            "O código expira em 30 minutos. Se você não pediu a troca, ignore esta mensagem.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    return token


def find_user_for_reset(enrollment="", email=""):
    if enrollment:
        profile = StudentProfile.objects.select_related("user").filter(enrollment=enrollment).first()
        return profile.user if profile else None
    if email:
        return User.objects.filter(email=email).first()
    return None


def create_admin_user(email, full_name, password):
    email = email.strip().lower()
    if User.objects.filter(email=email).exists():
        raise ValueError("Já existe um usuário com este e-mail.")
    if not re.fullmatch(r".+@.+\..+", email):
        raise ValueError("Informe um e-mail válido.")
    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValueError(" ".join(exc.messages)) from exc
    user = User(
        username=f"admin-{secrets.token_hex(4)}",
        email=email,
        full_name=" ".join(full_name.split()),
        role=User.Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )
    user.set_password(password)
    user.save()
    return user
