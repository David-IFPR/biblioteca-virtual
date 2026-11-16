import secrets

from apps.accounts.models import StudentProfile, User
from apps.accounts.serializers import create_admin_user
from apps.catalog.models import Category
from apps.catalog.services import create_book
from rest_framework_simplejwt.tokens import RefreshToken


def auth(client, user):
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")


def make_admin(email="admin@acervo.escola", password="Admin@12345"):
    return create_admin_user(email, "Coordenação da Biblioteca", password)


def make_student(
    enrollment="20260001",
    name="Helena Duarte",
    email=None,
    password="Aluno@12345",
):
    email = email or f"{enrollment.lower()}@aluno.acervo.escola"
    user = User(
        username=f"aluno-{enrollment}",
        email=email,
        full_name=name,
        role=User.Role.STUDENT,
        first_name=name.split()[0],
        last_name=" ".join(name.split()[1:]),
    )
    user.set_password(password)
    user.save()
    return StudentProfile.objects.create(user=user, enrollment=enrollment)


def make_book(actor, title="Dom Casmurro", quantity=2, isbn=None, category_name="Literatura"):
    category, _created = Category.objects.get_or_create(
        name=category_name, defaults={"description": "Obras desta área."}
    )
    if isbn is None:
        isbn = "978" + f"{secrets.randbelow(10**10):010d}"
    return create_book(
        {
            "title": title,
            "author": "Machado de Assis",
            "publisher": "Editora Escolar",
            "isbn": isbn,
            "publication_year": 1899,
            "category": category,
            "description": "Romance para consulta e empréstimo no acervo da instituição.",
            "shelf_location": "Estante A1",
        },
        quantity,
        actor,
    )
