from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        REQUEST_APPROVED = "request_approved", "Solicitação aprovada"
        REQUEST_REJECTED = "request_rejected", "Solicitação recusada"
        LOAN_REGISTERED = "loan_registered", "Empréstimo registrado"
        DUE_SOON = "due_soon", "Prazo próximo"
        OVERDUE = "overdue", "Empréstimo atrasado"
        RETURN_CONFIRMED = "return_confirmed", "Devolução confirmada"
        DUE_CHANGED = "due_changed", "Prazo alterado"
        NEW_LOAN_REQUEST = "new_loan_request", "Nova solicitação de empréstimo"
        NEW_RETURN_REQUEST = "new_return_request", "Nova solicitação de devolução"
        ADMIN_OVERDUE = "admin_overdue", "Empréstimo atrasado"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=40, choices=Kind.choices)
    title = models.CharField(max_length=140)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
