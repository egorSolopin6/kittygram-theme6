from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APITestCase
from cats.models import Cat
from .models import DailyTop, Vote
from .roles import configure_roles, OWNER_GROUP, READER_GROUP, VOTER_GROUP


class CatTestData:
    def setUp(self):
        self.owner = get_user_model().objects.create_user('owner', password='test-only-password')
        self.other = get_user_model().objects.create_user('other', password='test-only-password')
        self.groups = configure_roles()
        for user in (self.owner, self.other):
            user.groups.add(self.groups[OWNER_GROUP])
        self.cat = Cat.objects.create(name='Луна', color='black', birth_year=2022, owner=self.owner)
        self.cat2 = Cat.objects.create(name='Персик', color='orange', owner=self.other)
        self.today = timezone.localdate()


class ShowcaseTests(CatTestData, APITestCase):
    def vote(self, cat=None, data=None):
        return self.client.post(f'/api/cats/{(cat or self.cat).pk}/vote/', data or {})

    def test_public_showcase_and_private_cats(self):
        self.assertEqual(self.client.get('/api/cats/').status_code, 401)
        self.assertEqual(self.client.get('/cats/').status_code, 401)
        public = self.client.get('/api/showcase/cats/')
        self.assertEqual(public.status_code, 200)
        self.assertEqual(set(public.data['results'][0]), {'id', 'name', 'color'})
        self.assertEqual(self.vote().status_code, 401)
        self.assertEqual(self.client.get('/api/showcase/my-votes/').status_code, 401)
        self.assertEqual(self.client.post('/api/cats/', {'name': 'Кот', 'color': 'gray'}).status_code, 401)

    def test_vote_updates_score_and_prevents_second_choice(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.vote().status_code, 201)
        self.assertEqual(self.vote().status_code, 400)
        self.assertEqual(self.vote(self.cat2).status_code, 400)
        self.assertEqual(Vote.objects.count(), 1)
        self.assertEqual(DailyTop.objects.get(cat=self.cat).score, 1)

    def test_withdraw_and_vote_again(self):
        self.client.force_authenticate(self.owner)
        self.vote()
        self.assertEqual(self.client.delete(f'/api/cats/{self.cat.pk}/vote/').status_code, 204)
        self.assertEqual(DailyTop.objects.get(cat=self.cat).score, 0)
        self.assertEqual(self.client.delete(f'/api/cats/{self.cat.pk}/vote/').status_code, 404)
        self.assertEqual(self.vote(self.cat2).status_code, 201)

    def test_cannot_withdraw_another_users_vote(self):
        self.client.force_authenticate(self.owner)
        self.vote()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(f'/api/cats/{self.cat.pk}/vote/').status_code, 404)
        self.assertEqual(Vote.objects.count(), 1)

    def test_owner_permissions_and_server_assigned_owner(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f'/api/cats/{self.cat.pk}/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/cats/{self.cat.pk}/', {'name': 'Чужой'}).status_code, 404)
        self.assertEqual(self.client.delete(f'/api/cats/{self.cat.pk}/').status_code, 404)
        result = self.client.post('/api/cats/', {'name': 'Новый', 'color': 'gray', 'owner': self.owner.pk})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data['owner'], self.other.pk)

    def test_private_lists_and_legacy_alias_do_not_leak_cats(self):
        self.client.force_authenticate(self.owner)
        for url in ('/api/cats/', '/api/cats/mine/', '/cats/'):
            response = self.client.get(url)
            self.assertEqual([c['id'] for c in response.data['results']], [self.cat.pk])

    def test_staff_flag_does_not_bypass_ownership(self):
        self.other.is_staff = True
        self.other.save()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f'/api/cats/{self.cat.pk}/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/cats/{self.cat.pk}/', {'name': 'Чужой'}).status_code, 404)

    def test_reader_is_read_only_and_cannot_vote(self):
        self.owner.groups.set([self.groups[READER_GROUP]])
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(f'/api/cats/{self.cat.pk}/').status_code, 200)
        self.assertEqual(self.client.post('/api/cats/', {'name': 'Кот', 'color': 'gray'}).status_code, 403)
        self.assertEqual(self.client.patch(f'/api/cats/{self.cat.pk}/', {'name': 'Кот'}).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/cats/{self.cat.pk}/').status_code, 403)
        self.assertEqual(self.vote().status_code, 403)

    def test_voter_can_vote_but_has_no_private_cat_access(self):
        self.owner.groups.set([self.groups[VOTER_GROUP]])
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get('/api/cats/').status_code, 403)
        self.assertEqual(self.vote(self.cat2).status_code, 201)

    def test_superuser_sees_all_but_mine_still_only_own(self):
        self.owner.is_superuser = True
        self.owner.save()
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get('/api/cats/').data['count'], 2)
        self.assertEqual(self.client.get('/api/cats/mine/').data['count'], 1)
        self.assertEqual(self.client.patch(f'/api/cats/{self.cat2.pk}/', {'color': 'gray'}).status_code, 200)

    def test_user_without_group_cannot_manage_cats(self):
        self.owner.groups.clear()
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get('/api/cats/').status_code, 403)
        self.assertEqual(self.vote().status_code, 403)

    def test_dates_birth_year_and_vote_body_validation(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.vote(data={'score': 999}).status_code, 400)
        self.assertEqual(self.vote(data={'date': str(self.today - timedelta(days=1))}).status_code, 400)
        self.assertEqual(self.client.post('/api/cats/', {'name': 'Кот', 'color': 'gray', 'birth_year': self.today.year+1}).status_code, 400)
        self.assertEqual(self.client.get('/api/showcase/day/?date=bad').status_code, 400)
        self.assertEqual(self.client.get('/api/showcase/day/?date='+str(self.today+timedelta(days=1))).status_code, 400)
        self.assertEqual(self.client.get('/api/showcase/daily/?cat=abc').status_code, 400)

    def test_day_tie_break_and_empty_day(self):
        DailyTop.objects.create(cat=self.cat2, date=self.today, score=3)
        DailyTop.objects.create(cat=self.cat, date=self.today, score=3)
        result = self.client.get('/api/showcase/day/')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['cat']['id'], self.cat.pk)
        self.assertEqual(self.client.get('/api/showcase/day/?date='+str(self.today-timedelta(days=1))).status_code, 404)

    def test_week_window_sum_filter_and_pagination(self):
        DailyTop.objects.create(cat=self.cat, date=self.today, score=2)
        DailyTop.objects.create(cat=self.cat, date=self.today-timedelta(days=6), score=3)
        DailyTop.objects.create(cat=self.cat, date=self.today-timedelta(days=7), score=99)
        DailyTop.objects.create(cat=self.cat2, date=self.today, score=1)
        result = self.client.get('/api/showcase/week/?page_size=1')
        self.assertEqual(result.data['count'], 2)
        self.assertIsNotNone(result.data['next'])
        self.assertEqual(result.data['results'][0]['score'], 5)
        self.assertEqual(result.data['date_from'], str(self.today-timedelta(days=6)))
        filtered = self.client.get('/api/showcase/week/?color=orange')
        self.assertEqual(filtered.data['count'], 1)
        self.assertEqual(filtered.data['results'][0]['cat_id'], self.cat2.pk)

    def test_daily_filter_and_my_votes_privacy(self):
        self.client.force_authenticate(self.owner)
        self.vote()
        r = self.client.get(f'/api/showcase/daily/?date={self.today}&cat={self.cat.pk}&page_size=1')
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(self.client.get('/api/showcase/my-votes/').data['count'], 1)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/showcase/my-votes/').data['count'], 0)

    def test_database_uniqueness_and_protected_rating(self):
        self.client.force_authenticate(self.owner)
        self.vote()
        with self.assertRaises(IntegrityError), transaction.atomic():
            DailyTop.objects.create(cat=self.cat, date=self.today)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(user=self.owner, daily_top=DailyTop.objects.get(cat=self.cat), date=self.today)
        self.assertEqual(self.client.delete(f'/api/cats/{self.cat.pk}/').status_code, 400)

    def test_token_login(self):
        response = self.client.post('/api/auth/token/', {'username': 'owner', 'password': 'test-only-password'})
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION='Token '+response.data['token'])
        self.assertEqual(self.vote().status_code, 201)


class AdminPermissionsTests(CatTestData, TestCase):
    """Exercise Django admin using session login, not API authentication."""

    def setUp(self):
        super().setUp()
        self.owner.is_staff = True
        self.owner.save()
        self.client.force_login(self.owner)

    def test_admin_lists_only_own_and_rejects_foreign_urls(self):
        response = self.client.get('/admin/cats/cat/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['cl'].queryset), [self.cat])
        foreign_url = f'/admin/cats/cat/{self.cat2.pk}/change/'
        self.assertEqual(self.client.get(foreign_url).status_code, 302)
        self.client.post(foreign_url, {'name': 'Взлом', 'color': 'gray', '_save': 'Save'})
        self.cat2.refresh_from_db()
        self.assertEqual(self.cat2.name, 'Персик')
        for url in ('/admin/auth/user/', '/admin/auth/group/'):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_creation_ignores_forged_owner(self):
        response = self.client.post('/admin/cats/cat/add/', {
            'name': 'Свой', 'color': 'white', 'birth_year': 2024,
            'owner': self.other.pk, '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Cat.objects.get(name='Свой').owner, self.owner)

    def test_admin_reader_sees_own_without_edit_controls(self):
        self.owner.groups.set([self.groups[READER_GROUP]])
        response = self.client.get(f'/admin/cats/cat/{self.cat.pk}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['has_change_permission'])
        self.assertFalse(response.context['has_delete_permission'])
        self.assertEqual(self.client.post(f'/admin/cats/cat/{self.cat.pk}/change/', {
            'name': 'Взлом', 'color': 'gray', '_save': 'Save',
        }).status_code, 403)
        self.assertEqual(self.client.get('/admin/cats/cat/add/').status_code, 403)

    def test_admin_votes_are_private_and_rating_is_read_only(self):
        result = DailyTop.objects.create(cat=self.cat, date=self.today, score=2)
        own = Vote.objects.create(user=self.owner, daily_top=result, date=self.today)
        foreign = Vote.objects.create(user=self.other, daily_top=result, date=self.today)
        response = self.client.get('/admin/showcase/vote/')
        self.assertEqual(list(response.context['cl'].queryset), [own])
        self.assertEqual(self.client.get(f'/admin/showcase/vote/{foreign.pk}/change/').status_code, 302)
        response = self.client.get(f'/admin/showcase/dailytop/{result.pk}/change/')
        self.assertFalse(response.context['has_change_permission'])
        self.assertEqual(self.client.post(f'/admin/showcase/dailytop/{result.pk}/change/', {'score': 999}).status_code, 403)

    def test_admin_rejects_invalid_birth_year(self):
        response = self.client.post('/admin/cats/cat/add/', {
            'name': 'Ошибка', 'color': 'white', 'birth_year': self.today.year + 1, '_save': 'Save',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('birth_year', response.context['adminform'].form.errors)
        self.assertFalse(Cat.objects.filter(name='Ошибка').exists())
