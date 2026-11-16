from django.urls import path

from apps.circulation.admin_views import (
    AdminDashboardView,
    AdminLoanListView,
    AdminRequestListView,
    ApproveRequestView,
    ConfirmReturnView,
    DueDateView,
    MovementListView,
    PolicyView,
    RegisterLoanView,
    RejectRequestView,
    StudentBlockView,
    StudentDetailView,
    StudentListView,
    StudentUnblockView,
)

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("settings/", PolicyView.as_view(), name="admin-settings"),
    path("students/", StudentListView.as_view(), name="admin-students"),
    path("students/<int:pk>/", StudentDetailView.as_view(), name="admin-student"),
    path("students/<int:pk>/block/", StudentBlockView.as_view(), name="admin-student-block"),
    path("students/<int:pk>/unblock/", StudentUnblockView.as_view(), name="admin-student-unblock"),
    path("requests/", AdminRequestListView.as_view(), name="admin-requests"),
    path("requests/<int:pk>/approve/", ApproveRequestView.as_view(), name="admin-approve"),
    path("requests/<int:pk>/reject/", RejectRequestView.as_view(), name="admin-reject"),
    path("requests/<int:pk>/register-loan/", RegisterLoanView.as_view(), name="admin-register-loan"),
    path("loans/", AdminLoanListView.as_view(), name="admin-loans"),
    path("loans/<int:pk>/due-date/", DueDateView.as_view(), name="admin-due-date"),
    path("loans/<int:pk>/confirm-return/", ConfirmReturnView.as_view(), name="admin-confirm-return"),
    path("movements/", MovementListView.as_view(), name="admin-movements"),
]
