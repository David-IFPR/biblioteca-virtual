from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsStudentRole
from apps.catalog.models import Book, Category, Copy
from apps.catalog.serializers import BookSerializer, BookWriteSerializer, CategorySerializer, CopySerializer
from apps.catalog.services import book_queryset, change_copy_status, create_book, delete_book, update_book
from apps.common.exceptions import BusinessError
from apps.common.pagination import DefaultPagination

ORDERING = {
    "title": ("title", "id"),
    "-title": ("-title", "id"),
    "author": ("author", "title", "id"),
    "-author": ("-author", "title", "id"),
    "year": ("publication_year", "title", "id"),
    "-year": ("-publication_year", "title", "id"),
    "recent": ("-created_at", "id"),
}


class CategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [(IsStudentRole | IsAdminRole)()]
        return [IsAdminRole()]

    def get(self, request):
        categories = Category.objects.annotate(book_count=Count("books"))
        return Response(CategorySerializer(categories, many=True).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        category = get_object_or_404(Category.objects.annotate(book_count=Count("books")), pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        try:
            category.delete()
        except ProtectedError:
            return Response(
                {"detail": "Não é possível excluir uma categoria que ainda possui livros."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Categoria excluída."})


class BookListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [(IsStudentRole | IsAdminRole)()]
        return [IsAdminRole()]

    def get(self, request):
        queryset = book_queryset()
        params = request.query_params
        title = params.get("title", "").strip()
        author = params.get("author", "").strip()
        isbn = params.get("isbn", "").strip()
        query = params.get("q", "").strip()
        category = params.get("category", "").strip()
        available = params.get("available", "").strip().lower()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(author__icontains=query) | Q(isbn__icontains=query)
            )
        if title:
            queryset = queryset.filter(title__icontains=title)
        if author:
            queryset = queryset.filter(author__icontains=author)
        if isbn:
            queryset = queryset.filter(isbn__icontains=isbn)
        if category.isdigit():
            queryset = queryset.filter(category_id=int(category))
        if available in {"true", "1", "available"}:
            queryset = queryset.filter(available_copies__gt=0)
        elif available in {"false", "0", "unavailable"}:
            queryset = queryset.filter(available_copies=0)
        queryset = queryset.order_by(*ORDERING.get(params.get("ordering", "title"), ORDERING["title"]))
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BookSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = BookWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        quantity = data.pop("quantity")
        data.pop("remove_cover", None)
        try:
            book = create_book(data, quantity, request.user)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = BookSerializer(
            book_queryset().get(pk=book.pk), context={"request": request}
        ).data
        return Response(payload, status=status.HTTP_201_CREATED)


class BookDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [(IsStudentRole | IsAdminRole)()]
        return [IsAdminRole()]

    def get(self, request, pk):
        book = get_object_or_404(book_queryset(), pk=pk)
        data = BookSerializer(book, context={"request": request}).data
        if request.user.role == "student":
            from apps.circulation.services import request_eligibility

            allowed, reason = request_eligibility(request.user.student_profile, book)
            data["can_request"] = allowed
            data["request_block_reason"] = reason
        else:
            data["can_request"] = False
            data["request_block_reason"] = ""
        return Response(data)

    def patch(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        serializer = BookWriteSerializer(book, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        quantity = data.pop("quantity", None)
        remove_cover = data.pop("remove_cover", False)
        if remove_cover:
            if book.cover:
                book.cover.delete(save=False)
            data["cover"] = None
        try:
            update_book(book, data, quantity, request.user)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        payload = BookSerializer(book_queryset().get(pk=pk), context={"request": request}).data
        return Response(payload)

    def delete(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        try:
            delete_book(book, request.user)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return Response({"detail": "Livro excluído."})


class CopyStatusView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        copy = get_object_or_404(Copy, pk=pk)
        try:
            updated = change_copy_status(copy, request.data.get("status"), request.user)
        except BusinessError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return Response(CopySerializer(updated).data)
