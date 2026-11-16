from django.urls import path

from apps.circulation.student_views import (
    LoanRequestCreateView,
    MyCirculationView,
    RequestReturnView,
    StudentDashboardView,
)

urlpatterns = [
    path("dashboard/", StudentDashboardView.as_view(), name="student-dashboard"),
    path("circulation/", MyCirculationView.as_view(), name="student-circulation"),
    path("requests/", LoanRequestCreateView.as_view(), name="student-request"),
    path("loans/<int:pk>/request-return/", RequestReturnView.as_view(), name="student-return"),
]
