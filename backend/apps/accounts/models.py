import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Aluno"
        ADMIN = "admin", "Administrador"

    email = models.EmailField("e-mail", unique=True)
    full_name = models.CharField("nome completo", max_length=180)
    role = models.CharField("perfil", max_length=20, choices=Role.choices, default=Role.STUDENT)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "full_name"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        indexes = [models.Index(fields=["role"])]

    def __str__(self):
        return self.full_name or self.email

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        self.full_name = " ".join((self.full_name or "").split())
        super().save(*args, **kwargs)


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    enrollment = models.CharField("matrícula", max_length=20, unique=True, db_index=True)
    is_blocked = models.BooleanField("conta bloqueada", default=False)
    blocked_reason = models.CharField("motivo do bloqueio", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "aluno"
        verbose_name_plural = "alunos"
        ordering = ["enrollment"]

    def __str__(self):
        return f"{self.enrollment} — {self.user.full_name}"

    def save(self, *args, **kwargs):
        self.enrollment = (self.enrollment or "").strip().upper()
        super().save(*args, **kwargs)

    @property
    def account_status(self):
        if self.is_blocked or not self.user.is_active:
            return "blocked"
        return "active"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "token de redefinição"
        ordering = ["-created_at"]

    @classmethod
    def issue(cls, user, minutes=30):
        cls.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(minutes=minutes),
        )

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()
