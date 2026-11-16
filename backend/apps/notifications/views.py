from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsStudentRole
from apps.circulation.services import scan_due_notices
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import mark_read


class NotificationListView(APIView):
    permission_classes = [IsStudentRole | IsAdminRole]

    def get(self, request):
        scan_due_notices()
        queryset = Notification.objects.filter(recipient=request.user)
        unread = request.query_params.get("unread")
        if unread in {"1", "true"}:
            queryset = queryset.filter(is_read=False)
        from apps.common.pagination import DefaultPagination

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationSummaryView(APIView):
    permission_classes = [IsStudentRole | IsAdminRole]

    def get(self, request):
        scan_due_notices()
        return Response(
            {
                "unread": Notification.objects.filter(recipient=request.user, is_read=False).count()
            }
        )


class NotificationReadView(APIView):
    permission_classes = [IsStudentRole | IsAdminRole]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if notification is None:
            return Response({"detail": "Notificação não encontrada."}, status=404)
        mark_read(notification)
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    permission_classes = [IsStudentRole | IsAdminRole]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"detail": "Notificações marcadas como lidas."})
