from django.conf import settings
from django.db import models


class DailyTop(models.Model):
    date = models.DateField(db_index=True)
    cat = models.ForeignKey('cats.Cat', on_delete=models.PROTECT, related_name='daily_results')
    score = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ('-date', '-score', 'cat_id')
        constraints = [models.UniqueConstraint(fields=('date', 'cat'), name='unique_cat_day')]

    def __str__(self):
        return f'{self.date}: {self.cat} ({self.score})'


class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='showcase_votes')
    daily_top = models.ForeignKey(DailyTop, on_delete=models.CASCADE, related_name='votes')
    date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-date', '-id')
        constraints = [models.UniqueConstraint(fields=('user', 'date'), name='one_vote_per_user_day')]
