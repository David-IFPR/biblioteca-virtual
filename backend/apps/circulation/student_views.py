from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudentRole
from apps.catalog.serializers import BookSerializer
from apps.catalog.services import book_queryset
from apps.circulation.models import Loan, LoanRequest
from apps.circulation.serializers import LoanRequestSerializer, LoanSerializer
from apps.circulation.services import request_loan, request_return, scan_due_notices
from apps.common.exceptions import BusinessError
from apps.notifications.models import Notification


def loan_queryset():
    return Loan.objects.select_related(
        "book",
        "copy",
        "student__user",
        "confirmed_by",
        "registered_by",
    ).prefetch_related("due_date_changes__changed_by")


def request_queryset():
    return LoanRequest.objects.select_related(
        "book", "copy", "student__user", "reviewed_by"
    )


class StudentDashboardView(APIView):
    permission_classes = [IsStudentRole]

    def get(self, request):
        scan_due_notices()
        student = request.user.student_profile
        books = book_queryset()
        loans = loan_queryset().filter(student=student)
        requests = request_queryset().filter(student=student)
        today = timezone.localdate()
        active = loans.filter(status__in=Loan.OPEN)
        payload = {
            "student_name": student.user.full_name,
            "enrollment": student.enrollment,
            "available_books": books.filter(available_copies__gt=0).count(),
            "active_loans": active.count(),
            "pending_requests": requests.filter(status=LoanRequest.Status.PENDING).count(),
            "approved_requests": requests.filter(status=LoanRequest.Status.APPROVED).count(),
            "loan_history": loans.filter(status=Loan.Status.RETURNED).count(),
            "overdue_loans": active.filter(due_date__lt=today).count(),
            "unread_notifications": Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count(),
            "recent_books": BookSerializer(
                books.order_by("-created_at")[:6], many=True, context={"request": request}
            ).data,
            "featured_books": BookSerializer(
                books.filter(available_copies__gt=0).order_by("-created_at", "title")[:4],
                many=True,
                context={"request": request},
            ).data,
            "recent_loans": LoanSerializer(
                loans[:5], many=True, context={"request": request}
            ).data,
        }
        return Response(payload)


class MyCirculationView(APIView):
    permission_classes = [IsStudentRole]

    def get(self, request):
        scan_due_notices()
        student = request.user.student_profile
        loans = list(loan_queryset().filter(student=student)[:200])
        requests = list(request_queryset().filter(student=student)[:200])
        today = timezone.localdate()
        return Response(
            {
                "requests": LoanRequestSerializer(requests, many=True, context={"request": request}).data,
                "loans": LoanSerializer(loans, many=True, context={"request": request}).data,
                "counts": {
                    "pending": sum(1 for item in requests if item.status == LoanRequest.Status.PENDING),
                    "approved": sum(1 for item in requests if item.status == LoanRequest.Status.APPROVED),
                    "active": sum(1 for item in loans if item.status == Loan.Status.ACTIVE and item.due_date >= today),
                    "return_requested": sum(
                        1 for item in loans if item.status == Loan.Status.RETURN_REQUESTED
                    ),
                    "overdue": sum(
                        1 for item in loans if item.status in Loan.OPEN and item.due_date < today
                    ),
                    "returned": sum(1 for item in loans if item.status == Loan.Status.RETURNED),
                    "rejected": sum(1 for item in requests if item.status == LoanRequest.Status.REJECTED),
                },
            }
        )


class LoanRequestCreateView(APIView):
    permission_classes = [IsStudentRole]

    def post(self, request):
        try:
            loan_request = request_loan(request.user.student_profile, request.data.get("book_id"))
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = LoanRequestSerializer(
            request_queryset().get(pk=loan_request.pk), context={"request": request}
        ).data
        payload["detail"] = "Solicitação registrada. Aguarde a análise da biblioteca."
        return Response(payload, status=201)


class RequestReturnView(APIView):
    permission_classes = [IsStudentRole]

    def post(self, request, pk):
        try:
            loan = request_return(pk, request.user.student_profile)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = LoanSerializer(loan_queryset().get(pk=loan.pk), context={"request": request}).data
        payload["detail"] = (
            "Devolução solicitada. O livro continua emprestado até a biblioteca confirmar o recebimento."
        )
        return Response(payload)
