from django.contrib import admin
from cats.models import Cat
from .models import DailyTop, Vote

admin.site.site_header = 'Kittygram — управление'
admin.site.site_title = 'Kittygram'
admin.site.index_title = 'Коты, пользователи и рейтинг'


@admin.register(Cat)
class CatAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'color', 'birth_year', 'owner')
    list_filter = ('color',)
    search_fields = ('name',)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('owner')
        return qs if request.user.is_superuser else qs.filter(owner=request.user)

    def get_exclude(self, request, obj=None):
        return () if request.user.is_superuser else ('owner',)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

    def owns(self, request, obj):
        return obj is None or request.user.is_superuser or obj.owner_id == request.user.id

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self.owns(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self.owns(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self.owns(request, obj)


@admin.register(DailyTop)
class DailyTopAdmin(admin.ModelAdmin):
    list_display = ('date', 'cat', 'score')
    list_filter = ('date',)
    readonly_fields = ('date', 'cat', 'score')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_top', 'date')
    readonly_fields = ('user', 'daily_top', 'date', 'created_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'daily_top__cat')
        return qs if request.user.is_superuser else qs.filter(user=request.user)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and (
            obj is None or request.user.is_superuser or obj.user_id == request.user.id
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
