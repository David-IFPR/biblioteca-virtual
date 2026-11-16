from django.contrib import admin

from apps.catalog.models import Book, Category, Copy


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class CopyInline(admin.TabularInline):
    model = Copy
    extra = 0
    readonly_fields = ("inventory_code", "created_at")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "publication_year")
    search_fields = ("title", "author", "isbn")
    inlines = [CopyInline]
