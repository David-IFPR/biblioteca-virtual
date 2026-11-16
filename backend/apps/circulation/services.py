from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import StudentProfile, User
from apps.catalog.models import Book, Copy
from apps.circulation.audit import record_movement
from apps.circulation.models import DueDateChange, LibraryPolicy, Loan, LoanRequest, MovementLog
from apps.common.exceptions import BusinessError
from apps.notifications.services import notify_admins, notify_user


def _today():
    return timezone.localdate()


def commitment_count(student, exclude_request_id=None):
    requests = LoanRequest.objects.filter(student=student, status__in=LoanRequest.OPEN)
    if exclude_request_id:
        requests = requests.exclude(pk=exclude_request_id)
    loans = Loan.objects.filter(student=student, status__in=Loan.OPEN)
    return requests.count() + loans.count()


def request_eligibility(student, book):
    if student.is_blocked:
        return False, "Sua conta está bloqueada. Procure a biblioteca."
    policy = LibraryPolicy.load()
    available = book.copies.filter(status=Copy.Status.AVAILABLE).count()
    if available < 1:
        return False, "Não há exemplares disponíveis para empréstimo."
    existing = LoanRequest.objects.filter(student=student, book=book, status__in=LoanRequest.OPEN).first()
    if existing:
        if existing.status == LoanRequest.Status.APPROVED:
            return False, "Sua solicitação já foi aprovada. Retire o exemplar na biblioteca."
        return False, "Você já possui uma solicitação pendente para este livro."
    if Loan.objects.filter(student=student, book=book, status__in=Loan.OPEN).exists():
        return False, "Você já possui este livro emprestado."
    if commitment_count(student) >= policy.max_active_loans:
        return (
            False,
            f"Limite de {policy.max_active_loans} empréstimos ou solicitações simultâneas atingido.",
        )
    return True, ""


@transaction.atomic
def request_loan(student, book_id):
    try:
        book_id = int(book_id)
    except (TypeError, ValueError) as exc:
        raise BusinessError("Selecione um livro.") from exc
    student = StudentProfile.objects.select_for_update().select_related("user").get(pk=student.pk)
    if student.is_blocked:
        raise BusinessError("Sua conta está bloqueada. Procure a biblioteca.", status_code=403)
    try:
        book = Book.objects.select_for_update().get(pk=book_id)
    except Book.DoesNotExist as exc:
        raise BusinessError("Livro não encontrado.", status_code=404) from exc
    allowed, reason = request_eligibility(student, book)
    if not allowed:
        raise BusinessError(reason)
    loan_request = LoanRequest.objects.create(student=student, book=book, status=LoanRequest.Status.PENDING)
    record_movement(
        actor=student.user,
        action=MovementLog.Action.REQUEST_CREATED,
        description=f"{student.user.full_name} solicitou empréstimo de {book.title}.",
        student=student,
        book=book,
        loan_request=loan_request,
    )
    notify_admins(
        "new_loan_request",
        "Nova solicitação de empréstimo",
        f"{student.user.full_name} ({student.enrollment}) solicitou «{book.title}».",
    )
    return loan_request


def _available_copy(book):
    return (
        Copy.objects.select_for_update()
        .filter(book=book, status=Copy.Status.AVAILABLE)
        .order_by("id")
        .first()
    )


@transaction.atomic
def approve_request(request_id, admin):
    try:
        loan_request = (
            LoanRequest.objects.select_for_update()
            .select_related("book", "student__user")
            .get(pk=request_id)
        )
    except LoanRequest.DoesNotExist as exc:
        raise BusinessError("Solicitação não encontrada.", status_code=404) from exc
    if loan_request.status != LoanRequest.Status.PENDING:
        raise BusinessError("Somente solicitações pendentes podem ser aprovadas.")
    if loan_request.student.is_blocked:
        raise BusinessError("A conta do aluno está bloqueada.")
    policy = LibraryPolicy.load()
    if commitment_count(loan_request.student, exclude_request_id=loan_request.id) >= policy.max_active_loans:
        raise BusinessError("O aluno atingiu o limite de empréstimos simultâneos.")
    copy = _available_copy(loan_request.book)
    if copy is None:
        raise BusinessError(
            "Não há exemplar disponível. A solicitação permanece pendente e o exemplar não foi reservado."
        )
    copy.status = Copy.Status.RESERVED
    copy.save(update_fields=["status"])
    loan_request.copy = copy
    loan_request.status = LoanRequest.Status.APPROVED
    loan_request.reviewed_at = timezone.now()
    loan_request.reviewed_by = admin
    loan_request.save()
    record_movement(
        actor=admin,
        action=MovementLog.Action.REQUEST_APPROVED,
        description=(
            f"Solicitação de {loan_request.book.title} aprovada para "
            f"{loan_request.student.user.full_name}. Exemplar {copy.inventory_code} reservado."
        ),
        student=loan_request.student,
        book=loan_request.book,
        loan_request=loan_request,
        metadata={"copy_id": copy.id},
    )
    notify_user(
        loan_request.student.user,
        "request_approved",
        "Solicitação aprovada",
        f"Sua solicitação de «{loan_request.book.title}» foi aprovada. "
        "Dirija-se à biblioteca para retirar o exemplar.",
    )
    return loan_request


@transaction.atomic
def reject_request(request_id, admin, reason):
    reason = " ".join((reason or "").split())
    if len(reason) < 5:
        raise BusinessError("Informe o motivo da recusa.")
    try:
        loan_request = (
            LoanRequest.objects.select_for_update()
            .select_related("book", "student__user", "copy")
            .get(pk=request_id)
        )
    except LoanRequest.DoesNotExist as exc:
        raise BusinessError("Solicitação não encontrada.", status_code=404) from exc
    if loan_request.status != LoanRequest.Status.PENDING:
        raise BusinessError("Somente solicitações pendentes podem ser recusadas.")
    loan_request.status = LoanRequest.Status.REJECTED
    loan_request.rejection_reason = reason
    loan_request.reviewed_at = timezone.now()
    loan_request.reviewed_by = admin
    loan_request.save()
    record_movement(
        actor=admin,
        action=MovementLog.Action.REQUEST_REJECTED,
        description=f"Solicitação de {loan_request.book.title} recusada. Motivo: {reason}",
        student=loan_request.student,
        book=loan_request.book,
        loan_request=loan_request,
    )
    notify_user(
        loan_request.student.user,
        "request_rejected",
        "Solicitação recusada",
        f"Sua solicitação de «{loan_request.book.title}» foi recusada. Motivo: {reason}",
    )
    return loan_request


def _parse_due_date(value, default):
    if not value:
        return default
    if hasattr(value, "year") and not isinstance(value, str):
        return value
    try:
        year, month, day = str(value)[:10].split("-")
        from datetime import date

        return date(int(year), int(month), int(day))
    except (TypeError, ValueError) as exc:
        raise BusinessError("Informe uma data de devolução válida.") from exc


def _create_loan(*, student, book, copy, admin, due_date, loan_request=None):
    policy = LibraryPolicy.load()
    due = _parse_due_date(due_date, _today() + timedelta(days=policy.loan_days))
    if due < _today():
        raise BusinessError("A data de devolução não pode ser anterior a hoje.")
    loan = Loan.objects.create(
        student=student,
        book=book,
        copy=copy,
        request=loan_request,
        status=Loan.Status.ACTIVE,
        loaned_at=timezone.now(),
        due_date=due,
        registered_by=admin,
    )
    copy.status = Copy.Status.LOANED
    copy.save(update_fields=["status"])
    record_movement(
        actor=admin,
        action=MovementLog.Action.LOAN_REGISTERED,
        description=(
            f"Empréstimo de {book.title} registrado para {student.user.full_name}. "
            f"Devolução prevista em {due.strftime('%d/%m/%Y')}."
        ),
        student=student,
        book=book,
        loan=loan,
        loan_request=loan_request,
    )
    notify_user(
        student.user,
        "loan_registered",
        "Empréstimo registrado",
        f"A retirada de «{book.title}» foi registrada. Devolva até {due.strftime('%d/%m/%Y')}.",
    )
    return loan


@transaction.atomic
def register_loan_from_request(request_id, admin, due_date=None):
    try:
        loan_request = (
            LoanRequest.objects.select_for_update()
            .select_related("book", "student__user", "copy")
            .get(pk=request_id)
        )
    except LoanRequest.DoesNotExist as exc:
        raise BusinessError("Solicitação não encontrada.", status_code=404) from exc
    if loan_request.status != LoanRequest.Status.APPROVED or loan_request.copy_id is None:
        raise BusinessError("Aprove a solicitação antes de registrar a retirada.")
    copy = Copy.objects.select_for_update().get(pk=loan_request.copy_id)
    if copy.status != Copy.Status.RESERVED:
        raise BusinessError("O exemplar reservado não está disponível para retirada.")
    if Loan.objects.filter(copy=copy, status__in=Loan.OPEN).exists():
        raise BusinessError("Este exemplar já possui um empréstimo em aberto.")
    loan = _create_loan(
        student=loan_request.student,
        book=loan_request.book,
        copy=copy,
        admin=admin,
        due_date=due_date,
        loan_request=loan_request,
    )
    loan_request.status = LoanRequest.Status.FULFILLED
    loan_request.save(update_fields=["status"])
    return loan


@transaction.atomic
def register_direct_loan(student_id, book_id, admin, due_date=None):
    try:
        student = StudentProfile.objects.select_for_update().select_related("user").get(pk=int(student_id))
    except (StudentProfile.DoesNotExist, TypeError, ValueError) as exc:
        raise BusinessError("Aluno não encontrado.", status_code=404) from exc
    if student.is_blocked:
        raise BusinessError("A conta do aluno está bloqueada.")
    try:
        book = Book.objects.select_for_update().get(pk=int(book_id))
    except (Book.DoesNotExist, TypeError, ValueError) as exc:
        raise BusinessError("Livro não encontrado.", status_code=404) from exc
    policy = LibraryPolicy.load()
    if commitment_count(student) >= policy.max_active_loans:
        raise BusinessError("O aluno atingiu o limite de empréstimos simultâneos.")
    if Loan.objects.filter(student=student, book=book, status__in=Loan.OPEN).exists():
        raise BusinessError("O aluno já possui este livro emprestado.")
    if LoanRequest.objects.filter(student=student, book=book, status__in=LoanRequest.OPEN).exists():
        raise BusinessError(
            "Já existe uma solicitação em aberto deste livro. Aprove-a e registre a retirada por ela."
        )
    copy = _available_copy(book)
    if copy is None:
        raise BusinessError("Não há exemplar disponível para este empréstimo.")
    return _create_loan(student=student, book=book, copy=copy, admin=admin, due_date=due_date)


@transaction.atomic
def change_due_date(loan_id, new_due, reason, admin):
    reason = " ".join((reason or "").split())
    if len(reason) < 5:
        raise BusinessError("Informe o motivo da alteração de prazo.")
    try:
        loan = Loan.objects.select_for_update().select_related("book", "student__user").get(pk=loan_id)
    except Loan.DoesNotExist as exc:
        raise BusinessError("Empréstimo não encontrado.", status_code=404) from exc
    if loan.status not in Loan.OPEN:
        raise BusinessError("Só é possível alterar o prazo de um empréstimo em aberto.")
    parsed = _parse_due_date(new_due, None)
    if parsed is None:
        raise BusinessError("Informe a nova data de devolução.")
    if parsed < timezone.localtime(loan.loaned_at).date():
        raise BusinessError("A nova data não pode ser anterior ao dia da retirada.")
    if parsed == loan.due_date:
        raise BusinessError("A nova data é igual ao prazo atual.")
    previous = loan.due_date
    DueDateChange.objects.create(
        loan=loan,
        previous_due_date=previous,
        new_due_date=parsed,
        reason=reason,
        changed_by=admin,
    )
    loan.due_date = parsed
    loan.due_soon_notice_at = None
    loan.overdue_notice_at = None
    loan.save(update_fields=["due_date", "due_soon_notice_at", "overdue_notice_at", "updated_at"])
    record_movement(
        actor=admin,
        action=MovementLog.Action.DUE_DATE_CHANGED,
        description=(
            f"Prazo de {loan.book.title} alterado de {previous.strftime('%d/%m/%Y')} "
            f"para {parsed.strftime('%d/%m/%Y')}. Motivo: {reason}"
        ),
        student=loan.student,
        book=loan.book,
        loan=loan,
    )
    notify_user(
        loan.student.user,
        "due_changed",
        "Prazo de devolução alterado",
        f"O prazo de «{loan.book.title}» passou para {parsed.strftime('%d/%m/%Y')}.",
    )
    return loan


@transaction.atomic
def request_return(loan_id, student):
    try:
        loan = (
            Loan.objects.select_for_update()
            .select_related("book", "copy", "student__user")
            .get(pk=loan_id, student=student)
        )
    except Loan.DoesNotExist as exc:
        raise BusinessError("Empréstimo não encontrado.", status_code=404) from exc
    if loan.status == Loan.Status.RETURN_REQUESTED:
        raise BusinessError("A devolução deste livro já está aguardando confirmação da biblioteca.")
    if loan.status != Loan.Status.ACTIVE:
        raise BusinessError("Este empréstimo não está ativo.")
    loan.status = Loan.Status.RETURN_REQUESTED
    loan.return_requested_at = timezone.now()
    loan.save(update_fields=["status", "return_requested_at", "updated_at"])
    record_movement(
        actor=student.user,
        action=MovementLog.Action.RETURN_REQUESTED,
        description=(
            f"{student.user.full_name} solicitou a devolução de {loan.book.title}. "
            "O exemplar continua emprestado até a confirmação da biblioteca."
        ),
        student=student,
        book=loan.book,
        loan=loan,
    )
    notify_admins(
        "new_return_request",
        "Nova solicitação de devolução",
        f"{student.user.full_name} ({student.enrollment}) solicitou a devolução de «{loan.book.title}».",
    )
    return loan


@transaction.atomic
def confirm_return(loan_id, admin):
    try:
        loan = (
            Loan.objects.select_for_update()
            .select_related("book", "copy", "student__user")
            .get(pk=loan_id)
        )
    except Loan.DoesNotExist as exc:
        raise BusinessError("Empréstimo não encontrado.", status_code=404) from exc
    if loan.status == Loan.Status.RETURNED:
        raise BusinessError("Este empréstimo já foi devolvido.")
    if loan.status not in Loan.OPEN:
        raise BusinessError("Este empréstimo não pode ser devolvido.")
    copy = Copy.objects.select_for_update().get(pk=loan.copy_id)
    now = timezone.now()
    loan.status = Loan.Status.RETURNED
    loan.returned_at = now
    loan.confirmed_by = admin
    loan.save(update_fields=["status", "returned_at", "confirmed_by", "updated_at"])
    copy.status = Copy.Status.AVAILABLE
    copy.save(update_fields=["status"])
    record_movement(
        actor=admin,
        action=MovementLog.Action.RETURN_CONFIRMED,
        description=(
            f"Devolução de {loan.book.title} confirmada por {admin.full_name}. "
            f"Exemplar {copy.inventory_code} disponível novamente."
        ),
        student=loan.student,
        book=loan.book,
        loan=loan,
        metadata={"confirmed_by": admin.id, "copy_id": copy.id},
    )
    notify_user(
        loan.student.user,
        "return_confirmed",
        "Devolução confirmada",
        f"A biblioteca confirmou a devolução de «{loan.book.title}».",
    )
    return loan


def scan_due_notices():
    today = _today()
    policy = LibraryPolicy.load()
    soon_limit = today + timedelta(days=policy.reminder_days)
    open_loans = Loan.objects.select_related("student__user", "book")
    overdue = open_loans.filter(
        status__in=Loan.OPEN,
        due_date__lt=today,
        overdue_notice_at__isnull=True,
    )
    for loan in overdue:
        notify_user(
            loan.student.user,
            "overdue",
            "Empréstimo atrasado",
            f"O empréstimo de «{loan.book.title}» está atrasado desde {loan.due_date.strftime('%d/%m/%Y')}.",
        )
        notify_admins(
            "admin_overdue",
            "Empréstimo atrasado",
            f"O empréstimo de «{loan.book.title}» para {loan.student.user.full_name} está atrasado.",
        )
        loan.overdue_notice_at = timezone.now()
        loan.save(update_fields=["overdue_notice_at"])
    upcoming = open_loans.filter(
        status=Loan.Status.ACTIVE,
        due_date__gte=today,
        due_date__lte=soon_limit,
        due_soon_notice_at__isnull=True,
    )
    for loan in upcoming:
        notify_user(
            loan.student.user,
            "due_soon",
            "Prazo de devolução próximo",
            f"O prazo de «{loan.book.title}» termina em {loan.due_date.strftime('%d/%m/%Y')}.",
        )
        loan.due_soon_notice_at = timezone.now()
        loan.save(update_fields=["due_soon_notice_at"])


def display_status(loan):
    if loan.status == Loan.Status.ACTIVE and loan.due_date < _today():
        return "overdue"
    return loan.status


def is_overdue(loan):
    return loan.status in Loan.OPEN and loan.due_date < _today()


def student_queryset():
    from django.db.models import Count

    return StudentProfile.objects.select_related("user").annotate(
        loan_count=Count("loans", distinct=True),
        active_loan_count=Count("loans", filter=Q(loans__status__in=list(Loan.OPEN)), distinct=True),
    )


@transaction.atomic
def update_student(student, full_name, email, admin):
    email = email.strip().lower()
    full_name = " ".join(full_name.split())
    if len(full_name) < 5 or " " not in full_name:
        raise BusinessError("Informe o nome completo.")
    try:
        validate_email(email)
    except ValidationError as exc:
        raise BusinessError("Informe um e-mail válido.") from exc
    if User.objects.filter(email=email).exclude(pk=student.user_id).exists():
        raise BusinessError("Já existe um cadastro com este e-mail.")
    user = student.user
    user.full_name = full_name
    user.email = email
    user.first_name = full_name.split()[0]
    user.last_name = " ".join(full_name.split()[1:])
    user.save()
    record_movement(
        actor=admin,
        action=MovementLog.Action.STUDENT_UPDATED,
        description=f"Dados de {full_name} atualizados pela administração.",
        student=student,
    )
    return student


@transaction.atomic
def set_block(student, blocked, admin, reason=""):
    student.is_blocked = blocked
    student.blocked_reason = " ".join(reason.split()) if blocked else ""
    if blocked and len(student.blocked_reason) < 5:
        raise BusinessError("Informe o motivo do bloqueio.")
    student.save(update_fields=["is_blocked", "blocked_reason", "updated_at"])
    action = MovementLog.Action.STUDENT_BLOCKED if blocked else MovementLog.Action.STUDENT_UNBLOCKED
    verb = "bloqueada" if blocked else "desbloqueada"
    record_movement(
        actor=admin,
        action=action,
        description=f"Conta de {student.user.full_name} {verb}.",
        student=student,
        metadata={"reason": student.blocked_reason},
    )
    return student


@transaction.atomic
def update_policy(data, admin):
    LibraryPolicy.load()
    policy = LibraryPolicy.objects.select_for_update().get(pk=1)
    max_loans = int(data["max_active_loans"])
    loan_days = int(data["loan_days"])
    reminder_days = int(data["reminder_days"])
    if not 1 <= max_loans <= 20:
        raise BusinessError("O limite de empréstimos deve ficar entre 1 e 20.")
    if not 1 <= loan_days <= 180:
        raise BusinessError("O prazo padrão deve ficar entre 1 e 180 dias.")
    if not 1 <= reminder_days < loan_days:
        raise BusinessError("O aviso de prazo deve ser menor que o prazo padrão.")
    policy.max_active_loans = max_loans
    policy.loan_days = loan_days
    policy.reminder_days = reminder_days
    policy.save()
    record_movement(
        actor=admin,
        action=MovementLog.Action.POLICY_UPDATED,
        description=(
            f"Política atualizada: limite {max_loans}, prazo {loan_days} dias, "
            f"aviso com {reminder_days} dias."
        ),
        metadata=data,
    )
    return policy
