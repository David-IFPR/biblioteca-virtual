from django.conf import settings
from django.db import models

from apps.accounts.models import StudentProfile
from apps.catalog.models import Book, Copy


class LibraryPolicy(models.Model):
    max_active_loans = models.PositiveIntegerField("limite de empréstimos simultâneos", default=3)
    loan_days = models.PositiveIntegerField("prazo padrão em dias", default=14)
    reminder_days = models.PositiveIntegerField("avisar quantos dias antes", default=3)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "política da biblioteca"
        verbose_name_plural = "políticas da biblioteca"

    def __str__(self):
        return "Política de empréstimos"

    @classmethod
    def load(cls):
        policy, _created = cls.objects.get_or_create(
            pk=1,
            defaults={"max_active_loans": 3, "loan_days": 14, "reminder_days": 3},
        )
        return policy


class LoanRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Recusado"
        FULFILLED = "fulfilled", "Retirada registrada"
        CANCELLED = "cancelled", "Cancelado"

    OPEN = (Status.PENDING, Status.APPROVED)

    student = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="loan_requests"
    )
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loan_requests")
    copy = models.ForeignKey(
        Copy, null=True, blank=True, on_delete=models.PROTECT, related_name="reservations"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_requests",
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "solicitação de empréstimo"
        verbose_name_plural = "solicitações de empréstimo"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["book", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "book"],
                condition=models.Q(status__in=["pending", "approved"]),
                name="uniq_open_request_per_student_book",
            )
        ]

    def __str__(self):
        return f"{self.student.enrollment} — {self.book.title} ({self.status})"


class Loan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Emprestado"
        RETURN_REQUESTED = "return_requested", "Aguardando confirmação"
        RETURNED = "returned", "Devolvido"

    OPEN = (Status.ACTIVE, Status.RETURN_REQUESTED)

    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name="loans")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loans")
    copy = models.ForeignKey(Copy, on_delete=models.PROTECT, related_name="loans")
    request = models.ForeignKey(
        LoanRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="loans"
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    loaned_at = models.DateTimeField()
    due_date = models.DateField()
    return_requested_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_returns",
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="registered_loans",
    )
    due_soon_notice_at = models.DateTimeField(null=True, blank=True)
    overdue_notice_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "empréstimo"
        verbose_name_plural = "empréstimos"
        ordering = ["-loaned_at"]
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["status", "due_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["copy"],
                condition=models.Q(status__in=["active", "return_requested"]),
                name="uniq_open_loan_per_copy",
            )
        ]

    def __str__(self):
        return f"{self.student.enrollment} — {self.book.title}"


class DueDateChange(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="due_date_changes")
    previous_due_date = models.DateField()
    new_due_date = models.DateField()
    reason = models.TextField()
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="due_date_changes"
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "alteração de prazo"


class MovementLog(models.Model):
    class Action(models.TextChoices):
        REQUEST_CREATED = "request_created", "Solicitação criada"
        REQUEST_APPROVED = "request_approved", "Solicitação aprovada"
        REQUEST_REJECTED = "request_rejected", "Solicitação recusada"
        LOAN_REGISTERED = "loan_registered", "Empréstimo registrado"
        DUE_DATE_CHANGED = "due_date_changed", "Prazo alterado"
        RETURN_REQUESTED = "return_requested", "Devolução solicitada"
        RETURN_CONFIRMED = "return_confirmed", "Devolução confirmada"
        STUDENT_BLOCKED = "student_blocked", "Aluno bloqueado"
        STUDENT_UNBLOCKED = "student_unblocked", "Aluno desbloqueado"
        STUDENT_UPDATED = "student_updated", "Aluno atualizado"
        BOOK_CREATED = "book_created", "Livro cadastrado"
        BOOK_UPDATED = "book_updated", "Livro atualizado"
        BOOK_DELETED = "book_deleted", "Livro excluído"
        COPY_STATUS = "copy_status", "Disponibilidade alterada"
        POLICY_UPDATED = "policy_updated", "Política atualizada"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movements",
    )
    action = models.CharField(max_length=40, choices=Action.choices)
    description = models.TextField()
    student = models.ForeignKey(
        StudentProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )
    book = models.ForeignKey(
        Book, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )
    loan = models.ForeignKey(
        Loan, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )
    loan_request = models.ForeignKey(
        LoanRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "movimentação"
        verbose_name_plural = "movimentações"
        indexes = [models.Index(fields=["action", "-created_at"])]
