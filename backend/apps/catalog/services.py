import secrets

from django.db import transaction
from django.db.models import Count, Q

from apps.catalog.models import Book, Copy
from apps.common.exceptions import BusinessError


def book_queryset():
    return (
        Book.objects.select_related("category")
        .prefetch_related("copies")
        .annotate(
            total_copies=Count("copies", distinct=True),
            available_copies=Count(
                "copies",
                filter=Q(copies__status=Copy.Status.AVAILABLE),
                distinct=True,
            ),
        )
    )


def allocate_inventory_code():
    for _ in range(8):
        code = f"EX-{secrets.token_hex(3).upper()}"
        if not Copy.objects.filter(inventory_code=code).exists():
            return code
    raise BusinessError("Não foi possível gerar o código do exemplar. Tente novamente.")


def add_copies(book, amount):
    copies = []
    for _ in range(amount):
        copies.append(
            Copy(
                book=book,
                inventory_code=allocate_inventory_code(),
                status=Copy.Status.AVAILABLE,
                location=book.shelf_location,
            )
        )
    if copies:
        Copy.objects.bulk_create(copies)
    return copies


def set_copy_quantity(book, quantity):
    current = book.copies.count()
    if quantity == current:
        book.copies.update(location=book.shelf_location)
        return
    if quantity > current:
        add_copies(book, quantity - current)
        book.copies.update(location=book.shelf_location)
        return

    from apps.circulation.models import Loan, LoanRequest

    deficit = current - quantity
    candidates = list(
        book.copies.select_for_update()
        .filter(status=Copy.Status.AVAILABLE)
        .order_by("-id")
    )
    removable = []
    for copy in candidates:
        has_history = (
            Loan.objects.filter(copy=copy).exists()
            or LoanRequest.objects.filter(copy=copy).exists()
        )
        if not has_history:
            removable.append(copy)
        if len(removable) == deficit:
            break
    if len(removable) < deficit:
        raise BusinessError(
            "Não é possível reduzir a quantidade: há exemplares emprestados, reservados "
            "ou com histórico de movimentação. Indisponibilize exemplares ociosos ou "
            "aguarde a devolução."
        )
    Copy.objects.filter(pk__in=[copy.pk for copy in removable]).delete()
    book.copies.update(location=book.shelf_location)


@transaction.atomic
def create_book(data, quantity, actor):
    book = Book.objects.create(**data)
    add_copies(book, quantity)
    from apps.circulation.audit import record_movement
    from apps.circulation.models import MovementLog

    record_movement(
        actor=actor,
        action=MovementLog.Action.BOOK_CREATED,
        description=f"Livro cadastrado: {book.title} ({quantity} exemplar(es)).",
        book=book,
        metadata={"quantity": quantity},
    )
    return book


@transaction.atomic
def update_book(book, data, quantity, actor):
    locked = Book.objects.select_for_update().get(pk=book.pk)
    for field, value in data.items():
        setattr(locked, field, value)
    locked.save()
    if quantity is not None:
        set_copy_quantity(locked, quantity)
    else:
        locked.copies.update(location=locked.shelf_location)
    from apps.circulation.audit import record_movement
    from apps.circulation.models import MovementLog

    record_movement(
        actor=actor,
        action=MovementLog.Action.BOOK_UPDATED,
        description=f"Livro atualizado: {locked.title}.",
        book=locked,
    )
    return locked


@transaction.atomic
def delete_book(book, actor):
    from apps.circulation.audit import record_movement
    from apps.circulation.models import Loan, LoanRequest, MovementLog

    locked = Book.objects.select_for_update().get(pk=book.pk)
    open_statuses = [Loan.Status.ACTIVE, Loan.Status.RETURN_REQUESTED]
    if locked.copies.filter(status__in=[Copy.Status.LOANED, Copy.Status.RESERVED]).exists() or Loan.objects.filter(
        book=locked, status__in=open_statuses
    ).exists():
        raise BusinessError(
            "Não é possível excluir este livro porque existem empréstimos ou reservas em andamento."
        )
    if Loan.objects.filter(book=locked).exists() or LoanRequest.objects.filter(book=locked).exists():
        raise BusinessError(
            "Não é possível excluir este livro porque existem movimentações vinculadas no histórico."
        )
    title = locked.title
    record_movement(
        actor=actor,
        action=MovementLog.Action.BOOK_DELETED,
        description=f"Livro excluído: {title}.",
        metadata={"title": title, "book_id": locked.id},
    )
    locked.delete()


@transaction.atomic
def change_copy_status(copy, new_status, actor):
    from apps.circulation.audit import record_movement
    from apps.circulation.models import MovementLog

    locked = Copy.objects.select_for_update().select_related("book").get(pk=copy.pk)
    if new_status not in {Copy.Status.AVAILABLE, Copy.Status.UNAVAILABLE}:
        raise BusinessError("A situação do exemplar só pode ser alterada para disponível ou indisponível.")
    if locked.status in {Copy.Status.LOANED, Copy.Status.RESERVED}:
        raise BusinessError(
            "Este exemplar está emprestado ou reservado e não pode ter a disponibilidade alterada manualmente."
        )
    previous = locked.status
    locked.status = new_status
    locked.save(update_fields=["status"])
    record_movement(
        actor=actor,
        action=MovementLog.Action.COPY_STATUS,
        description=(
            f"Exemplar {locked.inventory_code} de {locked.book.title} "
            f"alterado de {previous} para {new_status}."
        ),
        book=locked.book,
        metadata={"copy_id": locked.id, "from": previous, "to": new_status},
    )
    return locked
