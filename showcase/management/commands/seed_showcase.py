import os
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from cats.models import Cat
from showcase.models import DailyTop, Vote
from showcase.roles import configure_roles, OWNER_GROUP, READER_GROUP, VOTER_GROUP


class Command(BaseCommand):
    help = 'Добавляет демонстрационных котов и согласованные голоса за последние семь дней без удаления данных.'

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get('DEMO_PASSWORD')
        if not password or password.startswith('replace-'):
            raise CommandError('Укажите DEMO_PASSWORD в окружении.')
        User = get_user_model()
        groups = configure_roles()
        users = {}
        for name in ['demo_admin', 'anna', 'boris', 'viewer'] + [f'demo_voter_{i:02}' for i in range(1, 13)]:
            user, created = User.objects.get_or_create(username=name)
            if created:
                user.set_password(password)
                user.is_superuser = name == 'demo_admin'
                user.save()
            user.is_staff = name in ['demo_admin', 'anna', 'boris', 'viewer']
            user.save(update_fields=['is_staff'])
            if name != 'demo_admin':
                role = READER_GROUP if name == 'viewer' else OWNER_GROUP if name in ['anna', 'boris'] else VOTER_GROUP
                user.groups.set([groups[role]])
            users[name] = user
        specs = [('Луна', 'black', 2022), ('Персик', 'orange', 2021),
                 ('Симба', 'golden', 2020), ('Мурка', 'gray', 2023),
                 ('Снежок', 'white', 2024), ('Марс', 'black', 2019),
                 ('Буся', 'tricolor', 2022), ('Тимоша', 'gray', 2021),
                 ('Нюша', 'white', 2023), ('Пиксель', 'black', 2024),
                 ('Зефир', 'white', 2025)]
        cats = []
        for i, (name, color, year) in enumerate(specs):
            cat, _ = Cat.objects.get_or_create(name=name, color=color, birth_year=year,
                                               owner=users['anna' if i % 2 == 0 else 'boris'])
            cats.append(cat)
        Cat.objects.get_or_create(name='Облако', color='white', birth_year=2024, owner=users['viewer'])
        today = timezone.localdate()
        for offset in range(7):
            day = today - timedelta(days=offset)
            allocation = [0, 0, 0, 0, 0, 1, 1, 1, 2, 3, 4 + offset % 6, 5 + offset % 5]
            for i, cat_index in enumerate(allocation[:10] if offset == 0 else allocation):
                user = users[f'demo_voter_{i+1:02}']
                if Vote.objects.filter(user=user, date=day).exists():
                    continue
                result, _ = DailyTop.objects.get_or_create(cat=cats[cat_index], date=day)
                Vote.objects.create(user=user, daily_top=result, date=day)
        # Счёт всегда восстанавливается из реальных демонстрационных и пользовательских голосов.
        for result in DailyTop.objects.annotate(actual_score=Count('votes')):
            if result.score != result.actual_score:
                DailyTop.objects.filter(pk=result.pk).update(score=result.actual_score)
        self.stdout.write(self.style.SUCCESS(
            f'Готово: {Cat.objects.count()} котов, {User.objects.count()} пользователей, '
            f'{DailyTop.objects.count()} дневных результатов, {Vote.objects.count()} голосов.'))
