import re

from django.core.validators import MinValueValidator
from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Book, Category, Copy

COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}


class CategorySerializer(serializers.ModelSerializer):
    book_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "book_count", "created_at"]
        read_only_fields = ["created_at"]

    def validate_name(self, value):
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise serializers.ValidationError("Informe o nome da categoria.")
        queryset = Category.objects.filter(name__iexact=cleaned)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe uma categoria com este nome.")
        return cleaned


class CopySerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Copy
        fields = ["id", "inventory_code", "status", "status_label", "location"]


class BookSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    total_copies = serializers.IntegerField(read_only=True)
    available_copies = serializers.IntegerField(read_only=True)
    cover_url = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    copy_summary = serializers.SerializerMethodField()
    copies = CopySerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "publisher",
            "isbn",
            "publication_year",
            "category",
            "category_name",
            "description",
            "cover_url",
            "shelf_location",
            "total_copies",
            "available_copies",
            "availability",
            "copy_summary",
            "copies",
            "created_at",
            "updated_at",
        ]

    def get_cover_url(self, obj):
        if not obj.cover:
            return None
        request = self.context.get("request")
        url = obj.cover.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_availability(self, obj):
        available = getattr(obj, "available_copies", None)
        if available is None:
            available = sum(1 for copy in obj.copies.all() if copy.status == Copy.Status.AVAILABLE)
        return "available" if available > 0 else "unavailable"

    def get_copy_summary(self, obj):
        summary = {choice: 0 for choice, _label in Copy.Status.choices}
        for copy in obj.copies.all():
            summary[copy.status] = summary.get(copy.status, 0) + 1
        summary["total"] = sum(summary.values())
        return summary


class BookWriteSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(min_value=1, max_value=500, write_only=True)
    remove_cover = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = Book
        fields = [
            "title",
            "author",
            "publisher",
            "isbn",
            "publication_year",
            "category",
            "description",
            "cover",
            "shelf_location",
            "quantity",
            "remove_cover",
        ]
        extra_kwargs = {
            "title": {"error_messages": {"blank": "Informe o título."}},
            "author": {"error_messages": {"blank": "Informe o autor."}},
            "publisher": {"error_messages": {"blank": "Informe a editora."}},
            "description": {"error_messages": {"blank": "Informe a descrição."}},
            "shelf_location": {"error_messages": {"blank": "Informe a localização física."}},
            "category": {"error_messages": {"required": "Selecione a categoria."}},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            quantity = self.fields["quantity"]
            quantity.required = False
            quantity.validators = [
                validator
                for validator in quantity.validators
                if not isinstance(validator, MinValueValidator)
            ]
            quantity.validators.append(MinValueValidator(0))

    def validate_title(self, value):
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise serializers.ValidationError("Informe o título.")
        return cleaned

    def validate_author(self, value):
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise serializers.ValidationError("Informe o autor.")
        return cleaned

    def validate_publisher(self, value):
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise serializers.ValidationError("Informe a editora.")
        return cleaned

    def validate_description(self, value):
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise serializers.ValidationError("A descrição deve ter pelo menos 10 caracteres.")
        return cleaned

    def validate_shelf_location(self, value):
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise serializers.ValidationError("Informe a localização física.")
        return cleaned

    def validate_isbn(self, value):
        digits = re.sub(r"[^0-9Xx]", "", value or "")
        if not digits:
            return None
        if len(digits) not in (10, 13) or not re.fullmatch(r"\d{9}[\dX]|\d{13}", digits.upper()):
            raise serializers.ValidationError("O ISBN deve ter 10 ou 13 dígitos.")
        normalized = digits.upper()
        queryset = Book.objects.filter(isbn=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um livro com este ISBN.")
        return normalized

    def validate_publication_year(self, value):
        limit = timezone.now().year + 1
        if value < 1450 or value > limit:
            raise serializers.ValidationError("Informe um ano de publicação válido.")
        return value

    def validate_cover(self, value):
        if value in (None, ""):
            return value
        content_type = getattr(value, "content_type", "") or ""
        if content_type and content_type not in COVER_TYPES:
            raise serializers.ValidationError("Envie a capa em JPG, PNG ou WEBP.")
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("A capa deve ter no máximo 2 MB.")
        return value

    def validate_quantity(self, value):
        if self.instance is None and value < 1:
            raise serializers.ValidationError("Cadastre pelo menos um exemplar.")
        if value < 0:
            raise serializers.ValidationError("A quantidade não pode ser negativa.")
        return value
