from django.urls import path, include
from django.contrib import admin
from django.views.generic import RedirectView
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from showcase.views import CatViewSet, PublicCatViewSet, DailyTopViewSet, CatOfDayView, WeeklyTopView, MyVotesView

from cats.views import cat_list

router = DefaultRouter()
router.register('cats', CatViewSet, basename='cat')
router.register('showcase/cats', PublicCatViewSet, basename='public-cat')
router.register('showcase/daily', DailyTopViewSet, basename='daily-top')

urlpatterns = [
   path('', RedirectView.as_view(url='/admin/', permanent=False)),
   path('health/', lambda request: JsonResponse({'status': 'ok'}), name='health'),
   path('cats/', cat_list),
   path('api/showcase/day/', CatOfDayView.as_view(), name='cat-of-day'),
   path('api/showcase/week/', WeeklyTopView.as_view(), name='weekly-top'),
   path('api/showcase/my-votes/', MyVotesView.as_view(), name='my-votes'),
   path('api/auth/token/', obtain_auth_token, name='api-token'),
   path('api/', include(router.urls)),
   path('api-auth/', include('rest_framework.urls')),
   path('admin/', admin.site.urls),
]


