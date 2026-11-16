from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import StudentProfile, User
from apps.accounts.permissions import IsAdminRole, IsStudentRole
from apps.accounts.serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
    find_user_for_reset,
    issue_reset,
)
from apps.accounts.validators import normalize_enrollment


def token_payload(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["full_name"] = user.full_name
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        payload = token_payload(user)
        payload["detail"] = "Cadastro realizado. Bem-vindo à biblioteca."
        return Response(payload, status=status.HTTP_201_CREATED)


class StudentLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        enrollment = normalize_enrollment(request.data.get("enrollment", ""))
        password = request.data.get("password", "")
        profile = (
            StudentProfile.objects.select_related("user").filter(enrollment=enrollment).first()
            if enrollment
            else None
        )
        user = profile.user if profile else None
        if user is None or user.role != User.Role.STUDENT or not user.check_password(password):
            return Response(
                {"detail": "Matrícula ou senha inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active or profile.is_blocked:
            return Response(
                {"detail": "Sua conta está bloqueada. Procure a biblioteca."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return Response(token_payload(user))


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password", "")
        user = User.objects.filter(email=email, role=User.Role.ADMIN).first()
        if user is None or not user.check_password(password):
            return Response(
                {"detail": "E-mail ou senha inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {"detail": "Esta conta administrativa está inativa."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return Response(token_payload(user))


class LogoutView(APIView):
    permission_classes = [IsStudentRole | IsAdminRole]

    def post(self, request):
        raw = request.data.get("refresh")
        if not raw:
            return Response(
                {"detail": "Informe o token de atualização para encerrar a sessão."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(raw)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Sessão já encerrada ou token inválido."}, status=400)
        return Response({"detail": "Sessão encerrada."})


class MeView(APIView):
    permission_classes = [IsStudentRole | IsAdminRole]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsStudentRole | IsAdminRole]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Senha alterada."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = find_user_for_reset(
            serializer.validated_data["enrollment"],
            serializer.validated_data["email"],
        )
        payload = {
            "detail": (
                "Se os dados corresponderem a uma conta, enviaremos as instruções de redefinição."
            )
        }
        if user and user.is_active:
            token = issue_reset(user)
            if settings.DEBUG:
                payload["debug_token"] = token.token
        return Response(payload)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["reset"]
        user = token.user
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return Response({"detail": "Senha redefinida. Entre com a nova senha."})


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
