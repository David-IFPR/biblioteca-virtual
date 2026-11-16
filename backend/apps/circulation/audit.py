from apps.circulation.models import MovementLog


def record_movement(
    *,
    actor,
    action,
    description,
    student=None,
    book=None,
    loan=None,
    loan_request=None,
    metadata=None,
):
    return MovementLog.objects.create(
        actor=actor,
        action=action,
        description=description,
        student=student,
        book=book,
        loan=loan,
        loan_request=loan_request,
        metadata=metadata or {},
    )
