from rest_framework.permissions import BasePermission

from apps.accounts.models import StudentProfile, User


class IsAdminRole(BasePermission):
    message = "Acesso restrito à administração da biblioteca."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == User.Role.ADMIN
        )


class IsStudentRole(BasePermission):
    message = "Acesso restrito aos alunos."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.role == User.Role.STUDENT):
            return False
        try:
            profile = user.student_profile
        except StudentProfile.DoesNotExist:
            return False
        if profile.is_blocked:
            self.message = "Sua conta está bloqueada. Procure a biblioteca."
            return False
        return True
