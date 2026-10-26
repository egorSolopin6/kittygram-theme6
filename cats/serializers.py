from rest_framework import serializers
from django.utils import timezone

from .models import Cat


class CatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cat
        fields = '__all__'
        read_only_fields = ('owner',)

    def validate_birth_year(self, value):
        if value is not None and not 1900 <= value <= timezone.localdate().year:
            raise serializers.ValidationError('Год рождения должен быть от 1900 до текущего года.')
        return value


class PublicCatSerializer(serializers.ModelSerializer):
    """Only fields intentionally published for voting."""
    class Meta:
        model = Cat
        fields = ('id', 'name', 'color')
        read_only_fields = fields
