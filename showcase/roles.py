from django.contrib.auth.models import Group, Permission

OWNER_GROUP = 'Владельцы котов'
READER_GROUP = 'Наблюдатели'
VOTER_GROUP = 'Участники голосования'


def configure_roles():
    common = ['view_dailytop', 'view_vote']
    rules = {
        OWNER_GROUP: ['view_cat', 'add_cat', 'change_cat', 'delete_cat', 'add_vote'] + common,
        READER_GROUP: ['view_cat'] + common,
        VOTER_GROUP: ['add_vote', 'view_vote'],
    }
    groups = {}
    for name, codenames in rules.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set(Permission.objects.filter(
            content_type__app_label__in=['cats', 'showcase'], codename__in=codenames))
        groups[name] = group
    return groups
