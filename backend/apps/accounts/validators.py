import re

from django.core.exceptions import ValidationError


class MinimumLengthValidator:
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(f"A senha deve ter pelo menos {self.min_length} caracteres.")

    def get_help_text(self):
        return f"A senha deve ter pelo menos {self.min_length} caracteres."


class NotNumericValidator:
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError("A senha não pode conter apenas números.")

    def get_help_text(self):
        return "A senha não pode conter apenas números."


ENROLLMENT_PATTERN = re.compile(r"^[A-Z0-9-]{4,20}$")


def normalize_enrollment(value):
    return (value or "").strip().upper()


def validate_enrollment(value):
    normalized = normalize_enrollment(value)
    if not ENROLLMENT_PATTERN.fullmatch(normalized):
        raise ValidationError(
            "A matrícula deve ter de 4 a 20 caracteres e usar apenas letras, números ou hífen."
        )
    return normalized
