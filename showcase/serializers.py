from rest_framework import serializers
from cats.serializers import PublicCatSerializer
from .models import DailyTop, Vote


class DailyTopSerializer(serializers.ModelSerializer):
    cat = PublicCatSerializer(read_only=True)

    class Meta:
        model = DailyTop
        fields = ('id', 'date', 'cat', 'score')
        read_only_fields = fields


class VoteSerializer(serializers.ModelSerializer):
    cat_id = serializers.IntegerField(source='daily_top.cat_id', read_only=True)
    cat_name = serializers.CharField(source='daily_top.cat.name', read_only=True)

    class Meta:
        model = Vote
        fields = ('id', 'date', 'cat_id', 'cat_name', 'created_at')
        read_only_fields = fields


class VoteInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if data:
            raise serializers.ValidationError({'non_field_errors': ['Тело запроса должно быть пустым. Дата, пользователь и скор определяются сервером.']})
        return {}
