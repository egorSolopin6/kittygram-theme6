from django.core.management.base import BaseCommand
from showcase.roles import configure_roles


class Command(BaseCommand):
    help = 'Обновляет группы доступа без изменения паролей пользователей.'

    def handle(self, *args, **options):
        self.stdout.write('Группы настроены: ' + ', '.join(configure_roles()))
