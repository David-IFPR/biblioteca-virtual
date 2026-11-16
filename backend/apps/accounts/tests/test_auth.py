from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import PasswordResetToken, User
from apps.common.factories import auth, make_admin, make_student


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_login_and_duplicate_enrollment(self):
        payload = {
            "full_name": "Helena Duarte",
            "enrollment": "2026-ab12",
            "email": "Helena@Aluno.escola",
            "password": "Aluno@12345",
            "password_confirm": "Aluno@12345",
        }
        created = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["user"]["enrollment"], "2026-AB12")
        self.assertEqual(created.data["user"]["role"], "student")
        user = User.objects.get(email="helena@aluno.escola")
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertNotIn("Aluno@12345", user.password)
        self.assertNotIn("password", created.data["user"])

        duplicate = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("matrícula", duplicate.data["detail"].lower())

        mismatch = self.client.post(
            "/api/auth/register/",
            {**payload, "enrollment": "20260099", "email": "outro@aluno.escola", "password_confirm": "outra"},
            format="json",
        )
        self.assertEqual(mismatch.status_code, 400)

        invalid_email = self.client.post(
            "/api/auth/register/",
            {**payload, "enrollment": "20260098", "email": "nao-e-email"},
            format="json",
        )
        self.assertEqual(invalid_email.status_code, 400)

        wrong = self.client.post(
            "/api/auth/login/",
            {"enrollment": "2026-AB12", "password": "errada"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 401)

        logged = self.client.post(
            "/api/auth/login/",
            {"enrollment": "2026-ab12", "password": "Aluno@12345"},
            format="json",
        )
        self.assertEqual(logged.status_code, 200, logged.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {logged.data['access']}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["full_name"], "Helena Duarte")

        anonymous = APIClient()
        blocked = anonymous.get("/api/catalog/books/")
        self.assertEqual(blocked.status_code, 401)

        admin_area = self.client.get("/api/admin/dashboard/")
        self.assertEqual(admin_area.status_code, 403)

    def test_blocked_student_cannot_login(self):
        student = make_student()
        student.is_blocked = True
        student.save()
        response = self.client.post(
            "/api/auth/login/",
            {"enrollment": student.enrollment, "password": "Aluno@12345"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_password_reset_and_logout(self):
        student = make_student()
        requested = self.client.post(
            "/api/auth/password-reset/",
            {"enrollment": student.enrollment},
            format="json",
        )
        self.assertEqual(requested.status_code, 200)
        token = PasswordResetToken.objects.get(user=student.user).token
        confirmed = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": token, "password": "NovaSenha@123", "password_confirm": "NovaSenha@123"},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        old = self.client.post(
            "/api/auth/login/",
            {"enrollment": student.enrollment, "password": "Aluno@12345"},
            format="json",
        )
        self.assertEqual(old.status_code, 401)
        fresh = self.client.post(
            "/api/auth/login/",
            {"enrollment": student.enrollment, "password": "NovaSenha@123"},
            format="json",
        )
        self.assertEqual(fresh.status_code, 200)
        logged_out = self.client.post(
            "/api/auth/logout/",
            {"refresh": fresh.data["refresh"]},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {fresh.data['access']}",
        )
        self.assertEqual(logged_out.status_code, 200)
        reused = self.client.post("/api/auth/refresh/", {"refresh": fresh.data["refresh"]}, format="json")
        self.assertEqual(reused.status_code, 401)

    def test_admin_login_rejects_student_email(self):
        make_admin()
        student = make_student()
        denied = self.client.post(
            "/api/auth/admin/login/",
            {"email": student.user.email, "password": "Aluno@12345"},
            format="json",
        )
        self.assertEqual(denied.status_code, 401)
        allowed = self.client.post(
            "/api/auth/admin/login/",
            {"email": "admin@acervo.escola", "password": "Admin@12345"},
            format="json",
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data["user"]["role"], "admin")
        auth(self.client, student.user)
        self.assertEqual(self.client.get("/api/admin/students/").status_code, 403)
