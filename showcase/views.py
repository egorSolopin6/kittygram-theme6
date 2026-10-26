from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from cats.models import Cat
from cats.serializers import CatSerializer, PublicCatSerializer
from .models import DailyTop, Vote
from .permissions import CatModelPermissions, IsCatOwnerOrSuperuser, CanVote
from .serializers import DailyTopSerializer, VoteSerializer, VoteInputSerializer


def query_date(request, key='date', default=None):
    raw = request.query_params.get(key)
    if raw is None:
        return default
    try:
        value = date.fromisoformat(raw)
        if value.isoformat() != raw:
            raise ValueError
    except (ValueError, TypeError):
        raise serializers.ValidationError({key: 'Нужна дата в формате YYYY-MM-DD.'})
    if value > timezone.localdate():
        raise serializers.ValidationError({key: 'Дата не может быть в будущем.'})
    return value


def query_cat(request):
    raw = request.query_params.get('cat')
    if raw is None:
        return None
    try:
        value = int(raw)
        if value < 1:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise serializers.ValidationError({'cat': 'Нужен положительный числовой ID кота.'})


class CatViewSet(viewsets.ModelViewSet):
    """Личные записи: только свои коты. Администратор видит всех."""
    serializer_class = CatSerializer
    permission_classes = (permissions.IsAuthenticated, CatModelPermissions, IsCatOwnerOrSuperuser)
    queryset = Cat.objects.select_related('owner').order_by('id')

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(owner=self.request.user)
        if 'color' in self.request.query_params:
            qs = qs.filter(color=self.request.query_params['color'])
        if 'search' in self.request.query_params:
            qs = qs.filter(name__icontains=self.request.query_params['search'])
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def mine(self, request):
        """Даже администратору этот список показывает только собственных котов."""
        qs = self.filter_queryset(self.get_queryset().filter(owner=request.user))
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def perform_destroy(self, instance):
        if instance.daily_results.exists():
            raise serializers.ValidationError({'cat': 'Кот участвует в рейтинге. Удаление истории голосов запрещено.'})
        instance.delete()

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated, CanVote],
            serializer_class=VoteInputSerializer)
    def vote(self, request, pk=None):
        """Один выбор в день. Пустой POST отдаёт голос, DELETE отзывает свой сегодняшний голос."""
        cat = get_object_or_404(Cat, pk=pk)
        today = timezone.localdate()
        if request.method == 'DELETE':
            with transaction.atomic():
                vote = get_object_or_404(Vote.objects.select_for_update(),
                                         user=request.user, date=today, daily_top__cat=cat)
                result_id = vote.daily_top_id
                vote.delete()
                DailyTop.objects.filter(pk=result_id, score__gt=0).update(score=F('score') - 1)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                if Vote.objects.filter(user=request.user, date=today).exists():
                    raise serializers.ValidationError({'vote': 'Вы уже голосовали сегодня. Сначала отзовите предыдущий голос.'})
                result, _ = DailyTop.objects.get_or_create(date=today, cat=cat)
                vote = Vote.objects.create(user=request.user, daily_top=result, date=today)
                DailyTop.objects.filter(pk=result.pk).update(score=F('score') + 1)
        except IntegrityError:
            raise serializers.ValidationError({'vote': 'Вы уже голосовали сегодня.'})
        return Response(VoteSerializer(vote).data, status=status.HTTP_201_CREATED)


class PublicCatViewSet(viewsets.ReadOnlyModelViewSet):
    """Витрина для голосования без владельцев и личных полей."""
    permission_classes = (permissions.AllowAny,)
    serializer_class = PublicCatSerializer
    queryset = Cat.objects.order_by('id')

    def get_queryset(self):
        qs = super().get_queryset()
        if 'color' in self.request.query_params:
            qs = qs.filter(color=self.request.query_params['color'])
        if 'search' in self.request.query_params:
            qs = qs.filter(name__icontains=self.request.query_params['search'])
        return qs


class DailyTopViewSet(viewsets.ReadOnlyModelViewSet):
    """Дневной рейтинг. Фильтры date и cat, страницы page и page_size."""
    permission_classes = (permissions.AllowAny,)
    serializer_class = DailyTopSerializer
    queryset = DailyTop.objects.select_related('cat').all()

    def get_queryset(self):
        qs = super().get_queryset()
        day = query_date(self.request)
        cat = query_cat(self.request)
        if day is not None:
            qs = qs.filter(date=day)
        if cat is not None:
            qs = qs.filter(cat_id=cat)
        return qs


class CatOfDayView(APIView):
    """Лидер дня. При равенстве баллов побеждает меньший ID кота. Без голосов ответ 404."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        day = query_date(request, default=timezone.localdate())
        result = DailyTop.objects.select_related('cat').filter(date=day, score__gt=0).order_by('-score', 'cat_id').first()
        if result is None:
            return Response({'detail': 'За эту дату ещё нет голосов.'}, status=404)
        return Response(DailyTopSerializer(result).data)


class WeeklyTopView(generics.GenericAPIView):
    """Сумма голосов за семь дат включительно до end_date (по умолчанию сегодня)."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        end = query_date(request, 'end_date', timezone.localdate())
        start = end - timedelta(days=6)
        qs = DailyTop.objects.filter(date__range=(start, end), score__gt=0)
        color = request.query_params.get('color')
        if color is not None:
            qs = qs.filter(cat__color=color)
        rows = list(qs.values('cat_id', 'cat__name', 'cat__color').annotate(score=Sum('score')).order_by('-score', 'cat_id'))
        rows = [{'rank': i + 1, 'cat_id': row['cat_id'], 'name': row['cat__name'],
                 'color': row['cat__color'], 'score': row['score']} for i, row in enumerate(rows)]
        page = self.paginate_queryset(rows)
        response = self.get_paginated_response(page)
        response.data['date_from'] = start.isoformat()
        response.data['date_to'] = end.isoformat()
        return response


class MyVotesView(generics.ListAPIView):
    """Только голоса текущего пользователя. Фильтры date и cat."""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = VoteSerializer

    def get_queryset(self):
        qs = Vote.objects.select_related('daily_top__cat').filter(user=self.request.user)
        day = query_date(self.request)
        cat = query_cat(self.request)
        if day is not None:
            qs = qs.filter(date=day)
        if cat is not None:
            qs = qs.filter(daily_top__cat_id=cat)
        return qs
