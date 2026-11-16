from django.db import models


class Category(models.Model):
    name = models.CharField("nome", max_length=80, unique=True)
    description = models.TextField("descrição", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = " ".join(self.name.split())
        super().save(*args, **kwargs)


class Book(models.Model):
    title = models.CharField("título", max_length=200)
    author = models.CharField("autor", max_length=180)
    publisher = models.CharField("editora", max_length=160)
    isbn = models.CharField("ISBN", max_length=13, unique=True, null=True, blank=True)
    publication_year = models.PositiveIntegerField("ano de publicação")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="books", verbose_name="categoria"
    )
    description = models.TextField("descrição")
    cover = models.ImageField("capa", upload_to="covers/", blank=True, null=True)
    shelf_location = models.CharField("localização física", max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "livro"
        verbose_name_plural = "livros"
        ordering = ["title", "id"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["author"]),
            models.Index(fields=["isbn"]),
        ]

    def __str__(self):
        return self.title


class Copy(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponível"
        RESERVED = "reserved", "Reservado"
        LOANED = "loaned", "Emprestado"
        UNAVAILABLE = "unavailable", "Indisponível"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    inventory_code = models.CharField("código do exemplar", max_length=20, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True
    )
    location = models.CharField("localização", max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "exemplar"
        verbose_name_plural = "exemplares"
        ordering = ["inventory_code"]
        indexes = [models.Index(fields=["book", "status"])]

    def __str__(self):
        return f"{self.inventory_code} ({self.book.title})"
