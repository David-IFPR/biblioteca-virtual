from django.core.management.base import BaseCommand, CommandError

from apps.accounts.serializers import create_admin_user


class Command(BaseCommand):
    help = "Cria o primeiro administrador da biblioteca."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        try:
            user = create_admin_user(options["email"], options["name"], options["password"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Administrador criado: {user.email}"))
