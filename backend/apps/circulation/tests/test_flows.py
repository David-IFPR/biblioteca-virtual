from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Copy
from apps.circulation.models import Loan
from apps.common.factories import auth, make_admin, make_book, make_student


class CirculationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.helena = make_student("20260001", "Helena Duarte", "helena@aluno.acervo.escola")
        self.miguel = make_student("20260002", "Miguel Alves", "miguel@aluno.acervo.escola")
        self.book = make_book(self.admin, title="Dom Casmurro", quantity=1, isbn="9788535911667")

    def test_full_loan_and_return_flow(self):
        auth(self.client, self.helena.user)
        requested = self.client.post(
            "/api/student/requests/", {"book_id": self.book.id}, format="json"
        )
        self.assertEqual(requested.status_code, 201, requested.data)
        self.assertEqual(requested.data["status"], "pending")
        self.book.refresh_from_db()
        self.assertEqual(
            Copy.objects.get(book=self.book).status,
            Copy.Status.AVAILABLE,
        )
        duplicate = self.client.post(
            "/api/student/requests/", {"book_id": self.book.id}, format="json"
        )
        self.assertEqual(duplicate.status_code, 400)

        auth(self.client, self.miguel.user)
        second = self.client.post(
            "/api/student/requests/", {"book_id": self.book.id}, format="json"
        )
        self.assertEqual(second.status_code, 201, second.data)

        auth(self.client, self.admin)
        approved = self.client.post(f"/api/admin/requests/{requested.data['id']}/approve/")
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(Copy.objects.get(book=self.book).status, Copy.Status.RESERVED)
        raced = self.client.post(f"/api/admin/requests/{second.data['id']}/approve/")
        self.assertEqual(raced.status_code, 400)
        self.assertIn("exemplar", raced.data["detail"].lower())
        self.assertEqual(
            Copy.objects.get(book=self.book).status,
            Copy.Status.RESERVED,
        )

        registered = self.client.post(
            f"/api/admin/requests/{requested.data['id']}/register-loan/",
            {"due_date": (timezone.localdate() + timedelta(days=7)).isoformat()},
            format="json",
        )
        self.assertEqual(registered.status_code, 201, registered.data)
        loan_id = registered.data["id"]
        copy = Copy.objects.get(book=self.book)
        self.assertEqual(copy.status, Copy.Status.LOANED)
        self.assertEqual(registered.data["status"], "active")

        auth(self.client, self.helena.user)
        illegal = self.client.post(f"/api/admin/loans/{loan_id}/confirm-return/")
        self.assertEqual(illegal.status_code, 403)
        copy.refresh_from_db()
        self.assertEqual(copy.status, Copy.Status.LOANED)
        loan = Loan.objects.get(pk=loan_id)
        self.assertEqual(loan.status, Loan.Status.ACTIVE)
        self.assertIsNone(loan.confirmed_by_id)

        asked = self.client.post(f"/api/student/loans/{loan_id}/request-return/", {"status": "returned"})
        self.assertEqual(asked.status_code, 200, asked.data)
        self.assertEqual(asked.data["status"], "return_requested")
        copy.refresh_from_db()
        self.assertEqual(copy.status, Copy.Status.LOANED)
        self.assertNotEqual(asked.data["status"], "returned")

        other = self.client.post(f"/api/student/loans/{loan_id}/request-return/")
        auth(self.client, self.miguel.user)
        stolen = self.client.post(f"/api/student/loans/{loan_id}/request-return/")
        self.assertEqual(stolen.status_code, 404)

        auth(self.client, self.admin)
        confirmed = self.client.post(f"/api/admin/loans/{loan_id}/confirm-return/")
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertEqual(confirmed.data["status"], "returned")
        self.assertEqual(confirmed.data["confirmed_by_name"], self.admin.full_name)
        copy.refresh_from_db()
        self.assertEqual(copy.status, Copy.Status.AVAILABLE)
        loan.refresh_from_db()
        self.assertEqual(loan.confirmed_by_id, self.admin.id)
        self.assertIsNotNone(loan.returned_at)

        removal = self.client.delete(f"/api/catalog/books/{self.book.id}/")
        self.assertEqual(removal.status_code, 400)
        self.assertIn("moviment", removal.data["detail"].lower())

    def test_direct_return_limit_and_rejection(self):
        other = make_book(self.admin, title="O Cortiço", quantity=2, isbn="9788535914842")
        auth(self.client, self.admin)
        self.client.patch(
            "/api/admin/settings/",
            {"max_active_loans": 1, "loan_days": 14, "reminder_days": 3},
            format="json",
        )
        direct = self.client.post(
            "/api/admin/loans/",
            {"student_id": self.helena.id, "book_id": self.book.id},
            format="json",
        )
        self.assertEqual(direct.status_code, 201, direct.data)
        self.assertEqual(Copy.objects.get(book=self.book).status, Copy.Status.LOANED)

        auth(self.client, self.helena.user)
        blocked = self.client.post("/api/student/requests/", {"book_id": other.id}, format="json")
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("limite", blocked.data["detail"].lower())

        auth(self.client, self.admin)
        refused_setup = self.client.post(
            "/api/student/requests/",
            {"book_id": other.id},
            format="json",
        )
        self.assertEqual(refused_setup.status_code, 403)

        auth(self.client, self.miguel.user)
        pending = self.client.post("/api/student/requests/", {"book_id": other.id}, format="json")
        self.assertEqual(pending.status_code, 201, pending.data)
        auth(self.client, self.admin)
        rejected = self.client.post(
            f"/api/admin/requests/{pending.data['id']}/reject/",
            {"reason": "Exemplar separado para consulta local."},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(rejected.data["status"], "rejected")
        self.assertEqual(
            Copy.objects.filter(book=other, status=Copy.Status.AVAILABLE).count(),
            2,
        )

        confirmed = self.client.post(f"/api/admin/loans/{direct.data['id']}/confirm-return/")
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertEqual(Copy.objects.get(book=self.book).status, Copy.Status.AVAILABLE)

        changed = self.client.post(
            "/api/admin/loans/",
            {"student_id": self.helena.id, "book_id": self.book.id},
            format="json",
        )
        self.assertEqual(changed.status_code, 201, changed.data)
        new_date = (timezone.localdate() + timedelta(days=21)).isoformat()
        updated = self.client.patch(
            f"/api/admin/loans/{changed.data['id']}/due-date/",
            {"due_date": new_date, "reason": "Prazo estendido por trabalho escolar."},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["due_date"], new_date)
        self.assertEqual(len(updated.data["due_date_changes"]), 1)

        auth(self.client, self.helena.user)
        hidden = self.client.get(f"/api/admin/students/{self.helena.id}/")
        self.assertEqual(hidden.status_code, 403)
        auth(self.client, self.admin)
        detail = self.client.get(f"/api/admin/students/{self.helena.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("password", detail.data)
        self.assertEqual(detail.data["enrollment"], "20260001")
        edited = self.client.patch(
            f"/api/admin/students/{self.helena.id}/",
            {
                "full_name": "Helena Duarte Lima",
                "email": "helena.lima@aluno.acervo.escola",
                "enrollment": "99999999",
                "is_blocked": True,
            },
            format="json",
        )
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(edited.data["enrollment"], "20260001")
        self.assertFalse(edited.data["is_blocked"])
        self.assertEqual(edited.data["full_name"], "Helena Duarte Lima")
