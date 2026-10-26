from rest_framework.permissions import BasePermission, DjangoModelPermissions


class CatModelPermissions(DjangoModelPermissions):
    perms_map = {
        **DjangoModelPermissions.perms_map,
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
    }


class IsCatOwnerOrSuperuser(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or obj.owner_id == request.user.id


class CanVote(BasePermission):
    message = 'Эта роль не разрешает голосование.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm('showcase.add_vote')
