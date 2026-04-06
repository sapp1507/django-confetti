from __future__ import annotations

import json

from django import forms
from django.contrib import admin, messages
from django.db.models import Count, QuerySet
from django.utils.html import escape, format_html

from .api import _ck  # внутренний хелпер для кэш-ключей
from .models import (
    SettingCategory,
    SettingDefinition,
    SettingScope,
    SettingsSnapshot,
    SettingType,
    SettingValue,
)
from .services import (
    build_global_settings_snapshot_payload,
    restore_global_settings_snapshot,
)
from .validators import validate_value


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


class SettingsSnapshotAdminForm(forms.ModelForm):
    class Meta:
        model = SettingsSnapshot
        fields = "__all__"


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
    from .models import SettingScope, SettingValue

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


@admin.action(description="Сохранить snapshot (снимок) всех глобальных настроек")
def create_settings_snapshot(modeladmin, request, queryset: QuerySet[SettingDefinition]):
    payload = build_global_settings_snapshot_payload()
    snapshot = SettingsSnapshot.objects.create(
        payload=payload,
        comment=f"Снимок через action, выбранных настроек: {queryset.count()}",
    )
    modeladmin.message_user(
        request,
        f"Создан снимок #{snapshot.pk}. В снимке: {len(payload)} настроек.",
        level=messages.SUCCESS,
    )


@admin.action(description="Восстановить настройки из snapshot (лишние настройки будут удалены)")
def restore_settings_snapshot(modeladmin, request, queryset: QuerySet[SettingsSnapshot]):
    snapshot = queryset.order_by("-created_at", "-id").first()
    if snapshot is None:
        modeladmin.message_user(request, "Не выбран снимок для восстановления.", level=messages.WARNING)
        return

    result = restore_global_settings_snapshot(snapshot.payload)
    modeladmin.message_user(
        request,
        (
            f"Восстановлен снимок #{snapshot.pk}. "
            f"Настроек создано: {result.created_definitions}, "
            f"обновлено: {result.updated_definitions}, "
            f"категорий создано: {result.created_categories}, "
            f"категорий обновлено: {result.updated_categories}, "
            f"глобальных значений обновлено: {result.updated_global_values}, "
            f"удалено лишних настроек: {result.deleted_definitions}."
        ),
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
    list_display = (
        "key",
        "title",
        "category",
        "type",
        "required",
        "enabled",
        "editable",
        "frontend",
        "values_count",
        "short_description",
    )
    list_filter = (
        "category",
        "type",
        "required",
        "enabled",
        "editable",
        "frontend",
        ("description", admin.EmptyFieldListFilter),
    )
    list_editable = (
        "required",
        "enabled",
        "editable",
        "frontend",
    )
    search_fields = ("key", "title", "description", "category__code", "category__title")
    ordering = ("category__code", "key")
    list_select_related = ("category",)
    list_display_links = ("key", "title")
    list_per_page = 50
    inlines = [SettingValueInline]
    actions = [clear_cache_for_definitions, create_settings_snapshot]
    autocomplete_fields = ()  # на будущее
    readonly_fields = ("values_count",)
    fieldsets = (
        ("Идентификация", {
            "fields": ("key", "title", "description", "category"),
        }),
        ("Тип и значения", {
            "fields": ("type", "default", "choices", "required"),
        }),
        ("Управление доступностью", {
            "fields": ("enabled", "editable", "frontend"),
        }),
        ("Статистика", {
            "fields": ("values_count",),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("category").annotate(_values_count=Count("values"))

    @admin.display(description="Значений", ordering="_values_count")
    def values_count(self, obj: SettingDefinition):
        return getattr(obj, "_values_count", 0)

    @admin.display(description="Описание")
    def short_description(self, obj: SettingDefinition):
        if not obj.description:
            return "—"
        text = obj.description.strip()
        return text if len(text) <= 120 else text[:117] + "…"


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


@admin.register(SettingsSnapshot)
class SettingsSnapshotAdmin(admin.ModelAdmin):
    form = SettingsSnapshotAdminForm
    list_display = ("id", "created_at", "comment", "settings_count")
    search_fields = ("comment",)
    readonly_fields = ("created_at", "settings_count", "restore_mechanics", "comparison_report", "pretty_payload")
    fields = ("created_at", "comment", "settings_count", "restore_mechanics", "comparison_report", "pretty_payload", "payload")
    actions = [restore_settings_snapshot]
    ordering = ("-created_at", "-id")

    @admin.display(description="Кол-во настроек")
    def settings_count(self, obj: SettingsSnapshot):
        return len(obj.payload or [])

    @admin.display(description="Содержимое снимка")
    def pretty_payload(self, obj: SettingsSnapshot):
        return json.dumps(obj.payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _build_snapshot_diff(
        snapshot_payload: list[dict],
        current_payload: list[dict],
    ) -> dict:
        snapshot_by_key = {item["key"]: item for item in snapshot_payload if item.get("key")}
        current_by_key = {item["key"]: item for item in current_payload if item.get("key")}

        snapshot_keys = set(snapshot_by_key)
        current_keys = set(current_by_key)

        only_in_snapshot = sorted(snapshot_keys - current_keys)
        only_in_current = sorted(current_keys - snapshot_keys)
        shared_keys = sorted(snapshot_keys & current_keys)

        changed: list[dict] = []
        unchanged_keys: list[str] = []

        for key in shared_keys:
            snapshot_item = snapshot_by_key[key]
            current_item = current_by_key[key]
            different_fields = sorted(
                field_name
                for field_name in (set(snapshot_item.keys()) | set(current_item.keys()))
                if snapshot_item.get(field_name) != current_item.get(field_name)
            )
            if different_fields:
                changed.append(
                    {
                        "key": key,
                        "different_fields": different_fields,
                        "snapshot": snapshot_item,
                        "current": current_item,
                    }
                )
            else:
                unchanged_keys.append(key)

        return {
            "counts": {
                "snapshot_total": len(snapshot_payload),
                "current_total": len(current_payload),
                "only_in_snapshot": len(only_in_snapshot),
                "only_in_current": len(only_in_current),
                "changed": len(changed),
                "unchanged": len(unchanged_keys),
            },
            "only_in_snapshot": [
                {"key": key, "snapshot": snapshot_by_key[key]}
                for key in only_in_snapshot
            ],
            "only_in_current": [
                {"key": key, "current": current_by_key[key]}
                for key in only_in_current
            ],
            "changed": changed,
            "unchanged_keys": unchanged_keys,
        }


    @admin.display(description="Как работает snapshot")
    def restore_mechanics(self, obj: SettingsSnapshot):
        return (
            "Restore применяет данные из payload к текущему реестру: "
            "обновляет существующие настройки, создает отсутствующие, "
            "обновляет глобальные значения и удаляет настройки, которых нет в snapshot."
        )

    @admin.display(description="Сравнение с текущими настройками")
    def comparison_report(self, obj: SettingsSnapshot):
        if obj.pk is None:
            return "Сохраните снимок, чтобы увидеть сравнение."

        current_payload = build_global_settings_snapshot_payload()
        diff = self._build_snapshot_diff(obj.payload or [], current_payload)
        rendered = escape(json.dumps(diff, ensure_ascii=False, indent=2))
        return format_html("<pre>{}</pre>", rendered)
