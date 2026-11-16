from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Copy
from apps.common.factories import auth, make_admin, make_book, make_student


class CatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.student = make_student()
        auth(self.client, self.admin)

    def _category(self):
        response = self.client.post(
            "/api/catalog/categories/",
            {"name": "História", "description": "Estudos históricos."},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def test_book_crud_search_and_protected_delete(self):
        category_id = self._category()
        created = self.client.post(
            "/api/catalog/books/",
            {
                "title": "História do Brasil",
                "author": "Equipe Acadêmica",
                "publisher": "Editora Campus",
                "isbn": "9788535902771",
                "publication_year": 2019,
                "category": category_id,
                "description": "Panorama didático para consulta dos estudantes.",
                "shelf_location": "Estante B3",
                "quantity": 2,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["available_copies"], 2)
        self.assertEqual(created.data["total_copies"], 2)
        book_id = created.data["id"]

        auth(self.client, self.student.user)
        denied = self.client.post("/api/catalog/books/", {"title": "Indevido"}, format="json")
        self.assertEqual(denied.status_code, 403)
        listed = self.client.get("/api/catalog/books/", {"title": "História", "available": "true"})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["count"], 1)
        by_isbn = self.client.get("/api/catalog/books/", {"isbn": "853590277"})
        self.assertEqual(by_isbn.data["count"], 1)

        auth(self.client, self.admin)
        updated = self.client.patch(
            f"/api/catalog/books/{book_id}/",
            {"quantity": 3, "author": "Equipe de História"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["available_copies"], 3)
        self.assertEqual(Copy.objects.filter(book_id=book_id).count(), 3)

        removed = self.client.delete(f"/api/catalog/books/{book_id}/")
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(Copy.objects.filter(book_id=book_id).exists())
