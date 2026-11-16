from rest_framework import serializers

from apps.accounts.models import StudentProfile
from apps.circulation.models import DueDateChange, LibraryPolicy, Loan, LoanRequest, MovementLog
from apps.circulation.services import display_status, is_overdue

STATUS_LABELS = {
    "pending": "Pendente",
    "approved": "Aprovado",
    "rejected": "Recusado",
    "fulfilled": "Retirada registrada",
    "cancelled": "Cancelado",
    "active": "Emprestado",
    "return_requested": "Aguardando confirmação",
    "returned": "Devolvido",
    "overdue": "Atrasado",
}


def cover_url(book, request):
    if not book.cover:
        return None
    if request is not None:
        return request.build_absolute_uri(book.cover.url)
    return book.cover.url


class LoanRequestSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(source="book.id", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_author = serializers.CharField(source="book.author", read_only=True)
    cover_url = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="student.user.full_name", read_only=True)
    enrollment = serializers.CharField(source="student.enrollment", read_only=True)
    copy_code = serializers.CharField(source="copy.inventory_code", read_only=True)
    status_label = serializers.SerializerMethodField()
    available_copies = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "book_id",
            "book_title",
            "book_author",
            "cover_url",
            "student_name",
            "enrollment",
            "student",
            "copy_code",
            "status",
            "status_label",
            "available_copies",
            "requested_at",
            "reviewed_at",
            "reviewed_by_name",
            "rejection_reason",
        ]

    def get_cover_url(self, obj):
        return cover_url(obj.book, self.context.get("request"))

    def get_status_label(self, obj):
        return STATUS_LABELS.get(obj.status, obj.status)

    def get_available_copies(self, obj):
        annotated = getattr(obj.book, "available_copies", None)
        if annotated is not None:
            return annotated
        from apps.catalog.models import Copy

        return obj.book.copies.filter(status=Copy.Status.AVAILABLE).count()

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by_id is None:
            return None
        return obj.reviewed_by.full_name


class DueDateChangeSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True)

    class Meta:
        model = DueDateChange
        fields = [
            "id",
            "previous_due_date",
            "new_due_date",
            "reason",
            "changed_by_name",
            "changed_at",
        ]


class LoanSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(source="book.id", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_author = serializers.CharField(source="book.author", read_only=True)
    cover_url = serializers.SerializerMethodField()
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    student_name = serializers.CharField(source="student.user.full_name", read_only=True)
    enrollment = serializers.CharField(source="student.enrollment", read_only=True)
    copy_code = serializers.CharField(source="copy.inventory_code", read_only=True)
    display_status = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    confirmed_by_name = serializers.SerializerMethodField()
    registered_by_name = serializers.SerializerMethodField()
    due_date_changes = DueDateChangeSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id",
            "book_id",
            "book_title",
            "book_author",
            "cover_url",
            "student_id",
            "student_name",
            "enrollment",
            "copy_code",
            "status",
            "display_status",
            "status_label",
            "is_overdue",
            "loaned_at",
            "due_date",
            "return_requested_at",
            "returned_at",
            "confirmed_by_name",
            "registered_by_name",
            "due_date_changes",
        ]

    def get_cover_url(self, obj):
        return cover_url(obj.book, self.context.get("request"))

    def get_display_status(self, obj):
        return display_status(obj)

    def get_status_label(self, obj):
        shown = display_status(obj)
        if obj.status == Loan.Status.RETURN_REQUESTED and is_overdue(obj):
            return "Aguardando confirmação"
        return STATUS_LABELS.get(shown, shown)

    def get_is_overdue(self, obj):
        return is_overdue(obj)

    def get_confirmed_by_name(self, obj):
        return obj.confirmed_by.full_name if obj.confirmed_by_id else None

    def get_registered_by_name(self, obj):
        return obj.registered_by.full_name if obj.registered_by_id else None


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    created_at = serializers.DateTimeField(source="user.date_joined", read_only=True)
    loan_count = serializers.IntegerField(read_only=True)
    active_loan_count = serializers.IntegerField(read_only=True)
    account_status = serializers.CharField(read_only=True)
    account_status_label = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "full_name",
            "enrollment",
            "email",
            "created_at",
            "loan_count",
            "active_loan_count",
            "is_blocked",
            "blocked_reason",
            "account_status",
            "account_status_label",
        ]

    def get_account_status_label(self, obj):
        return "Bloqueada" if obj.account_status == "blocked" else "Ativa"


class MovementSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    student_name = serializers.SerializerMethodField()
    book_title = serializers.SerializerMethodField()

    class Meta:
        model = MovementLog
        fields = [
            "id",
            "action",
            "action_label",
            "description",
            "actor_name",
            "student_name",
            "book_title",
            "created_at",
        ]

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor_id else "Sistema"

    def get_student_name(self, obj):
        return obj.student.user.full_name if obj.student_id else None

    def get_book_title(self, obj):
        return obj.book.title if obj.book_id else obj.metadata.get("title")


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryPolicy
        fields = ["max_active_loans", "loan_days", "reminder_days", "updated_at"]
