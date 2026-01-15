from rest_framework import serializers
from .models import SettingDefinition, SettingValue, SettingScope
from .validators import validate_value

class SettingItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    category = serializers.CharField()
    title = serializers.CharField()
    type = serializers.CharField()
    default = serializers.JSONField(allow_null=True)
    global_value = serializers.JSONField(allow_null=True)
    user_value = serializers.JSONField(allow_null=True)
    effective = serializers.JSONField(allow_null=True)
    frontend = serializers.BooleanField()
    required = serializers.BooleanField()
    editable = serializers.BooleanField()


class SettingWriteSerializer(serializers.Serializer):
    value = serializers.JSONField(allow_null=True)
    scope = serializers.ChoiceField(choices=SettingScope.choices, required=False)

    def validate(self, attrs):
        defn = self.context['definition']
        value = attrs.get('value')
        validated_value = validate_value(defn, value)
        attrs['value'] = validated_value
        return attrs
