from django.urls import path

from apps.catalog.views import (
    BookDetailView,
    BookListCreateView,
    CategoryDetailView,
    CategoryListCreateView,
    CopyStatusView,
)

urlpatterns = [
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path("books/", BookListCreateView.as_view(), name="book-list"),
    path("books/<int:pk>/", BookDetailView.as_view(), name="book-detail"),
    path("copies/<int:pk>/status/", CopyStatusView.as_view(), name="copy-status"),
]
