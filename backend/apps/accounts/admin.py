from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import PasswordResetToken, StudentProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("full_name", "email", "role", "is_active")
    search_fields = ("full_name", "email", "username")
    fieldsets = (
        (None, {"fields": ("email", "username", "password", "role")}),
        ("Identificação", {"fields": ("full_name", "first_name", "last_name")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "full_name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "user", "is_blocked", "created_at")
    search_fields = ("enrollment", "user__full_name", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "used_at")
    readonly_fields = ("token", "created_at", "expires_at", "used_at", "user")
