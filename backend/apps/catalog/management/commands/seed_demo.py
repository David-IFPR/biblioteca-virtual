from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.serializers import create_admin_user
from apps.catalog.models import Book, Category, Copy
from apps.catalog.services import create_book
from apps.circulation.models import DueDateChange, Loan, LoanRequest, MovementLog
from apps.circulation.services import (
    approve_request,
    change_due_date,
    register_loan_from_request,
    request_loan,
    request_return,
    scan_due_notices,
)
from apps.common.factories import make_student
from apps.notifications.models import Notification


BOOKS = [
    ("Dom Casmurro", "Machado de Assis", "Livraria Garnier", "9788535911667", 1899, "Literatura", "Estante A1", 4,
     "Romance narrado por Bento Santiago, usado nas leituras de literatura brasileira."),
    ("O Cortiço", "Aluísio Azevedo", "Editora Ática", "9788508169144", 1890, "Literatura", "Estante A1", 3,
     "Romance naturalista sobre o cotidiano de um cortiço no Rio de Janeiro."),
    ("Vidas Secas", "Graciliano Ramos", "Editora Record", "9788501115487", 1938, "Literatura", "Estante A2", 2,
     "Narrativa sobre uma família de retirantes no sertão."),
    ("Capitães da Areia", "Jorge Amado", "Companhia das Letras", "9788535914064", 1937, "Literatura", "Estante A2", 3,
     "História de meninos que vivem nas ruas de Salvador."),
    ("A Hora da Estrela", "Clarice Lispector", "Rocco", "9788532509475", 1977, "Literatura", "Estante A3", 2,
     "Novela sobre Macabéa e o olhar de quem conta a sua história."),
    ("Grande Sertão: Veredas", "Guimarães Rosa", "Companhia das Letras", "9788535924260", 1956, "Literatura", "Estante A3", 2,
     "Romance de Riobaldo sobre travessias, escolhas e o sertão."),
    ("Matemática para o Ensino Médio", "Equipe Acadêmica", "Editora Didática", "9786580001001", 2022, "Didáticos", "Estante C1", 5,
     "Material de apoio com funções, geometria e estatística básica."),
    ("Introdução à Programação", "Marina Lopes", "Editora Técnica", "9786580001002", 2023, "Tecnologia", "Estante D2", 4,
     "Primeiros passos em lógica, algoritmos e resolução de problemas."),
    ("Biologia Celular", "Paulo Nogueira", "Editora Ciência", "9786580001003", 2021, "Ciências", "Estante B2", 3,
     "Estrutura da célula, organelas e noções de genética."),
    ("Geografia do Brasil", "Helena Martins", "Editora Atlas", "9786580001004", 2020, "História", "Estante B4", 3,
     "Regiões, território, população e questões ambientais do país."),
    ("Arte e Percepção", "Lúcia Ferreira", "Editora Forma", "9786580001005", 2018, "Artes", "Estante E1", 2,
     "Introdução à leitura de imagens, cor e composição."),
    ("Química Geral", "Rafael Pires", "Editora Ciência", "9786580001006", 2019, "Ciências", "Estante B1", 4,
     "Átomos, ligações e reações para o ensino médio."),
]


class Command(BaseCommand):
    help = "Cria administrador, categorias, livros e movimentações de demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Apaga os dados atuais antes de recriar.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._wipe()
        elif Book.objects.exists():
            self.stdout.write("O acervo já possui livros. Use --reset para recriar a demonstração.")
            return

        admin = User.objects.filter(email="admin@acervo.escola").first()
        if admin is None:
            admin = create_admin_user(
                "admin@acervo.escola",
                "Coordenação da Biblioteca",
                "Admin@12345",
            )
        categories = {}
        for name, description in [
            ("Literatura", "Romances, contos e poesia."),
            ("Ciências", "Biologia, química e ciências da natureza."),
            ("História", "História e geografia."),
            ("Tecnologia", "Computação e cultura digital."),
            ("Didáticos", "Materiais de apoio às disciplinas."),
            ("Artes", "Artes visuais e percepção."),
        ]:
            categories[name], _created = Category.objects.get_or_create(
                name=name, defaults={"description": description}
            )

        created = {}
        for title, author, publisher, isbn, year, category, location, quantity, description in BOOKS:
            created[title] = create_book(
                {
                    "title": title,
                    "author": author,
                    "publisher": publisher,
                    "isbn": isbn,
                    "publication_year": year,
                    "category": categories[category],
                    "description": description,
                    "shelf_location": location,
                },
                quantity,
                admin,
            )

        helena = make_student("20260001", "Helena Duarte", "helena@aluno.acervo.escola")
        miguel = make_student("20260002", "Miguel Alves", "miguel@aluno.acervo.escola")
        livia = make_student("20260003", "Lívia Ramos", "livia@aluno.acervo.escola")

        first = request_loan(helena, created["Dom Casmurro"].id)
        approve_request(first.id, admin)
        loan = register_loan_from_request(first.id, admin)
        change_due_date(
            loan.id,
            (timezone.localdate() + timedelta(days=6)).isoformat(),
            "Prazo alinhado ao calendário da turma.",
            admin,
        )

        second = request_loan(helena, created["O Cortiço"].id)
        approve_request(second.id, admin)
        returning = register_loan_from_request(second.id, admin)
        request_return(returning.id, helena)

        third = request_loan(miguel, created["Vidas Secas"].id)
        approve_request(third.id, admin)
        overdue = register_loan_from_request(third.id, admin)
        overdue.due_date = timezone.localdate() - timedelta(days=4)
        overdue.overdue_notice_at = None
        overdue.save(update_fields=["due_date", "overdue_notice_at", "updated_at"])

        waiting = request_loan(miguel, created["Capitães da Areia"].id)
        approve_request(waiting.id, admin)
        request_loan(livia, created["A Hora da Estrela"].id)
        scan_due_notices()

        self.stdout.write(self.style.SUCCESS("Demonstração criada."))
        self.stdout.write("Administrador: admin@acervo.escola / Admin@12345")
        self.stdout.write("Alunos: matrículas 20260001, 20260002 e 20260003 / Aluno@12345")

    def _wipe(self):
        DueDateChange.objects.all().delete()
        Loan.objects.all().delete()
        LoanRequest.objects.all().delete()
        MovementLog.objects.all().delete()
        Notification.objects.all().delete()
        Copy.objects.all().delete()
        Book.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(role=User.Role.STUDENT).delete()
