from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import StudentProfile
from apps.accounts.permissions import IsAdminRole
from apps.catalog.models import Book, Copy
from apps.circulation.models import LibraryPolicy, Loan, LoanRequest, MovementLog
from apps.circulation.serializers import (
    LoanRequestSerializer,
    LoanSerializer,
    MovementSerializer,
    PolicySerializer,
    StudentSerializer,
)
from apps.circulation.services import (
    approve_request,
    change_due_date,
    confirm_return,
    register_direct_loan,
    register_loan_from_request,
    reject_request,
    scan_due_notices,
    set_block,
    student_queryset,
    update_policy,
    update_student,
)
from apps.circulation.student_views import loan_queryset, request_queryset
from apps.common.exceptions import BusinessError
from apps.common.pagination import DefaultPagination


def _page(request, queryset, serializer):
    paginator = DefaultPagination()
    page = paginator.paginate_queryset(queryset, request, view=request.parser_context["view"])
    return paginator.get_paginated_response(serializer(page, many=True, context={"request": request}).data)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        scan_due_notices()
        today = timezone.localdate()
        open_loans = Loan.objects.filter(status__in=Loan.OPEN)
        available = Copy.objects.filter(status=Copy.Status.AVAILABLE).count()
        loaned = Copy.objects.filter(status=Copy.Status.LOANED).count()
        reserved = Copy.objects.filter(status=Copy.Status.RESERVED).count()
        pending = LoanRequest.objects.filter(status=LoanRequest.Status.PENDING).count()
        returns_waiting = Loan.objects.filter(status=Loan.Status.RETURN_REQUESTED).count()
        overdue = open_loans.filter(due_date__lt=today).count()
        chart = [
            {"label": "Disponíveis", "value": available},
            {"label": "Emprestados", "value": loaned},
            {"label": "Reservados", "value": reserved},
            {"label": "Atrasados", "value": overdue},
            {"label": "Devoluções a confirmar", "value": returns_waiting},
            {"label": "Solicitações pendentes", "value": pending},
        ]
        return Response(
            {
                "books": Book.objects.count(),
                "copies": Copy.objects.count(),
                "available_copies": available,
                "loaned_copies": loaned,
                "reserved_copies": reserved,
                "pending_requests": pending,
                "approved_waiting_pickup": LoanRequest.objects.filter(
                    status=LoanRequest.Status.APPROVED
                ).count(),
                "returns_waiting": returns_waiting,
                "overdue": overdue,
                "students": StudentProfile.objects.count(),
                "active_loans": Loan.objects.filter(status=Loan.Status.ACTIVE).count(),
                "chart": chart,
                "recent_requests": LoanRequestSerializer(
                    request_queryset().filter(status=LoanRequest.Status.PENDING)[:5],
                    many=True,
                    context={"request": request},
                ).data,
                "overdue_loans": LoanSerializer(
                    loan_queryset().filter(status__in=Loan.OPEN, due_date__lt=today)[:5],
                    many=True,
                    context={"request": request},
                ).data,
                "recent_movements": MovementSerializer(
                    MovementLog.objects.select_related("actor", "student__user", "book")[:6],
                    many=True,
                ).data,
            }
        )


class PolicyView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(PolicySerializer(LibraryPolicy.load()).data)

    def patch(self, request):
        try:
            policy = update_policy(request.data, request.user)
        except (BusinessError, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, BusinessError):
                return Response({"detail": exc.message}, status=exc.status_code)
            return Response({"detail": "Informe limite, prazo e dias de aviso."}, status=400)
        return Response(PolicySerializer(policy).data)


class StudentListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        queryset = student_queryset()
        query = request.query_params.get("q", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        if query:
            queryset = queryset.filter(
                Q(user__full_name__icontains=query)
                | Q(enrollment__icontains=query)
                | Q(user__email__icontains=query)
            )
        if status_filter == "blocked":
            queryset = queryset.filter(is_blocked=True)
        elif status_filter == "active":
            queryset = queryset.filter(is_blocked=False, user__is_active=True)
        queryset = queryset.order_by("user__full_name")
        return _page(request, queryset, StudentSerializer)


class StudentDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        student = get_object_or_404(student_queryset(), pk=pk)
        data = StudentSerializer(student).data
        data["loans"] = LoanSerializer(
            loan_queryset().filter(student=student), many=True, context={"request": request}
        ).data
        data["requests"] = LoanRequestSerializer(
            request_queryset().filter(student=student), many=True, context={"request": request}
        ).data
        return Response(data)

    def patch(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
        try:
            update_student(
                student,
                request.data.get("full_name", ""),
                request.data.get("email", ""),
                request.user,
            )
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return Response(StudentSerializer(student_queryset().get(pk=pk)).data)


class StudentBlockView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
        try:
            set_block(student, True, request.user, request.data.get("reason", ""))
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return Response(StudentSerializer(student_queryset().get(pk=pk)).data)


class StudentUnblockView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        student = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
        try:
            set_block(student, False, request.user)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return Response(StudentSerializer(student_queryset().get(pk=pk)).data)


class AdminRequestListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        queryset = request_queryset()
        status_filter = request.query_params.get("status", "").strip()
        query = request.query_params.get("q", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if query:
            queryset = queryset.filter(
                Q(student__user__full_name__icontains=query)
                | Q(student__enrollment__icontains=query)
                | Q(book__title__icontains=query)
            )
        return _page(request, queryset, LoanRequestSerializer)


class ApproveRequestView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        try:
            loan_request = approve_request(pk, request.user)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = LoanRequestSerializer(
            request_queryset().get(pk=loan_request.pk), context={"request": request}
        ).data
        payload["detail"] = "Solicitação aprovada e exemplar reservado."
        return Response(payload)


class RejectRequestView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        try:
            loan_request = reject_request(pk, request.user, request.data.get("reason", ""))
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = LoanRequestSerializer(
            request_queryset().get(pk=loan_request.pk), context={"request": request}
        ).data
        payload["detail"] = "Solicitação recusada."
        return Response(payload)


class RegisterLoanView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        try:
            loan = register_loan_from_request(pk, request.user, request.data.get("due_date"))
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = LoanSerializer(loan_queryset().get(pk=loan.pk), context={"request": request}).data
        payload["detail"] = "Retirada registrada. O exemplar está emprestado."
        return Response(payload, status=201)


class AdminLoanListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        queryset = loan_queryset()
        status_filter = request.query_params.get("status", "").strip()
        query = request.query_params.get("q", "").strip()
        today = timezone.localdate()
        if status_filter == "overdue":
            queryset = queryset.filter(status__in=Loan.OPEN, due_date__lt=today)
        elif status_filter == "open":
            queryset = queryset.filter(status__in=Loan.OPEN)
        elif status_filter:
            queryset = queryset.filter(status=status_filter)
        if query:
            queryset = queryset.filter(
                Q(student__user__full_name__icontains=query)
                | Q(student__enrollment__icontains=query)
                | Q(book__title__icontains=query)
                | Q(copy__inventory_code__icontains=query)
            )
        return _page(request, queryset, LoanSerializer)

    def post(self, request):
        try:
            loan = register_direct_loan(
                request.data.get("student_id"),
                request.data.get("book_id"),
                request.user,
                request.data.get("due_date"),
            )
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = LoanSerializer(loan_queryset().get(pk=loan.pk), context={"request": request}).data
        payload["detail"] = "Empréstimo registrado."
        return Response(payload, status=201)


class DueDateView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        try:
            loan = change_due_date(
                pk, request.data.get("due_date"), request.data.get("reason", ""), request.user
            )
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return Response(LoanSerializer(loan_queryset().get(pk=loan.pk), context={"request": request}).data)


class ConfirmReturnView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        try:
            loan = confirm_return(pk, request.user)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = LoanSerializer(loan_queryset().get(pk=loan.pk), context={"request": request}).data
        payload["detail"] = "Devolução confirmada. O exemplar voltou a ficar disponível."
        return Response(payload)


class MovementListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        queryset = MovementLog.objects.select_related("actor", "student__user", "book")
        query = request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(description__icontains=query)
                | Q(actor__full_name__icontains=query)
                | Q(student__user__full_name__icontains=query)
                | Q(book__title__icontains=query)
            )
        return _page(request, queryset, MovementSerializer)
