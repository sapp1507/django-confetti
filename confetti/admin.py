from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.db.models import QuerySet

from .models import (
    SettingCategory,
    SettingDefinition,
    SettingValue,
    SettingScope,
    SettingType,
)
from .validators import validate_value
from .api import _ck  # внутренний хелпер для кэш-ключей


# ---------------------------
# Forms с типовой валидацией
# ---------------------------

class SettingDefinitionAdminForm(forms.ModelForm):
    class Meta:
        model = SettingDefinition
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        defn: SettingDefinition = self.instance
        # при создании defn ещё нет pk, читаем из cleaned
        defn.type = cleaned.get("type", defn.type)
        defn.choices = cleaned.get("choices", defn.choices)
        defn.default = cleaned.get("default", defn.default)

        # простая проверка структуры choices для CHOICE
        if defn.type == SettingType.CHOICE and defn.choices:
            bad = [c for c in defn.choices if not isinstance(c, dict) or "value" not in c]
            if bad:
                raise forms.ValidationError(
                    'Для типа CHOICE поле \'choices\' должно быть списком объектов вида '
                    '[{"value": ..., "label": "..."}, ...].'
                )

        # валидируем default согласно типу
        try:
            if defn.default is not None:
                validate_value(defn, defn.default)
        except Exception as e:
            raise forms.ValidationError(f'Некорректное значение по умолчанию (default): {e}')

        return cleaned


class SettingValueAdminForm(forms.ModelForm):
    class Meta:
        model = SettingValue
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        defn: SettingDefinition | None = cleaned.get("definition") or getattr(self.instance, "definition", None)
        value = cleaned.get("value", None)
        if defn is None:
            return cleaned
        try:
            # приведёт типы и проверит CHOICE/CRON/RRULE/JSON и т.п.
            validate_value(defn, value)
        except Exception as e:
            raise forms.ValidationError(f"Некорректное значение: {e}")
        return cleaned


# ---------------------------
# Inlines
# ---------------------------

class SettingValueInline(admin.TabularInline):
    model = SettingValue
    form = SettingValueAdminForm
    extra = 0
    raw_id_fields = ("user",)
    fields = ("scope", "user", "value")
    ordering = ("scope", "user")


# ---------------------------
# Admin actions
# ---------------------------

@admin.action(description="Очистить кэш для выбранных настроек")
def clear_cache_for_definitions(modeladmin, request, queryset: QuerySet[SettingDefinition]):
    from django.core.cache import cache
    from .models import SettingValue, SettingScope

    cleared = 0
    for d in queryset:
        # глобальный
        if cache.delete(_ck(d.key, None)):
            cleared += 1
        # пользовательские
        user_ids = SettingValue.objects.filter(
            definition=d, scope=SettingScope.USER
        ).values_list("user_id", flat=True)
        for uid in user_ids:
            if cache.delete(_ck(d.key, uid)):
                cleared += 1

    modeladmin.message_user(
        request,
        f"Инвалидировано кэш-ключей: {cleared}",
        level=messages.SUCCESS,
    )


# ---------------------------
# ModelAdmins
# ---------------------------

@admin.register(SettingCategory)
class SettingCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "title")
    search_fields = ("code", "title")
    prepopulated_fields = {"code": ("title",)}
    ordering = ("code",)


@admin.register(SettingDefinition)
class SettingDefinitionAdmin(admin.ModelAdmin):
    form = SettingDefinitionAdminForm
    list_display = ("key", "category", "type", "enabled", "editable")
    list_filter = ("category", "type", "enabled", "editable")
    search_fields = ("key", "title", "description")
    ordering = ("key",)
    inlines = [SettingValueInline]
    actions = [clear_cache_for_definitions]
    autocomplete_fields = ()  # на будущее
    readonly_fields = ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("category")


@admin.register(SettingValue)
class SettingValueAdmin(admin.ModelAdmin):
    form = SettingValueAdminForm
    list_display = ("definition_key", "scope", "user", "short_value")
    list_filter = ("scope", "definition__category", "definition__type")
    search_fields = ("definition__key", "definition__title", "user__username", "user__email")
    raw_id_fields = ("user", "definition")
    ordering = ("definition__key", "scope", "user")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("definition", "definition__category", "user")

    @admin.display(description="definition", ordering="definition__key")
    def definition_key(self, obj: SettingValue):
        return obj.definition.key

    @admin.display(description="value")
    def short_value(self, obj: SettingValue):
        v = obj.value
        s = str(v)
        return s if len(s) <= 120 else s[:117] + "…"
