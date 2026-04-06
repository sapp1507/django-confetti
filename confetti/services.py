from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.cache import cache
from django.db import transaction

from .api import _ck, _is_enabled_ck
from .models import (
    SettingCategory,
    SettingDefinition,
    SettingScope,
    SettingValue,
)


SETTING_DEFINITION_SNAPSHOT_FIELDS = (
    "key",
    "type",
    "title",
    "description",
    "default",
    "choices",
    "required",
    "enabled",
    "editable",
    "frontend",
)


@dataclass
class RestoreResult:
    created_definitions: int = 0
    updated_definitions: int = 0
    created_categories: int = 0
    updated_categories: int = 0
    updated_global_values: int = 0
    deleted_definitions: int = 0


def build_global_settings_snapshot_payload() -> list[dict[str, Any]]:
    definitions = (
        SettingDefinition.objects
        .select_related("category")
        .prefetch_related("values")
        .order_by("key")
    )

    payload: list[dict[str, Any]] = []
    for definition in definitions:
        global_value_obj = next(
            (
                value
                for value in definition.values.all()
                if value.scope == SettingScope.GLOBAL and value.user_id is None
            ),
            None,
        )

        item = {
            field_name: getattr(definition, field_name)
            for field_name in SETTING_DEFINITION_SNAPSHOT_FIELDS
        }
        item["category"] = None
        if definition.category:
            item["category"] = {
                "code": definition.category.code,
                "title": definition.category.title,
            }
        item["has_global_value"] = global_value_obj is not None
        item["global_value"] = global_value_obj.value if global_value_obj else None
        payload.append(item)

    return payload


@transaction.atomic
def restore_global_settings_snapshot(payload: list[dict[str, Any]]) -> RestoreResult:
    result = RestoreResult()

    snapshot_keys = {
        item.get("key")
        for item in payload
        if item.get("key")
    }
    stale_definitions = SettingDefinition.objects.exclude(key__in=snapshot_keys)

    stale_keys = list(stale_definitions.values_list("key", flat=True))
    result.deleted_definitions = stale_definitions.count()
    stale_definitions.delete()

    for stale_key in stale_keys:
        cache.delete(_ck(stale_key, None))
        cache.delete(_is_enabled_ck(stale_key, None))

    for item in payload:
        category_obj = None
        category_data = item.get("category")
        if category_data and category_data.get("code"):
            category_defaults = {"title": category_data.get("title", category_data["code"])}
            category_obj, created_category = SettingCategory.objects.get_or_create(
                code=category_data["code"],
                defaults=category_defaults,
            )
            if created_category:
                result.created_categories += 1
            elif category_data.get("title") is not None and category_obj.title != category_data["title"]:
                category_obj.title = category_data["title"]
                category_obj.save(update_fields=["title"])
                result.updated_categories += 1

        defaults = {
            field_name: item.get(field_name)
            for field_name in SETTING_DEFINITION_SNAPSHOT_FIELDS
            if field_name != "key"
        }
        defaults["category"] = category_obj

        definition, created_definition = SettingDefinition.objects.get_or_create(
            key=item["key"],
            defaults=defaults,
        )

        if created_definition:
            result.created_definitions += 1
        else:
            changed_fields: list[str] = []
            for field_name, field_value in defaults.items():
                if getattr(definition, field_name) != field_value:
                    setattr(definition, field_name, field_value)
                    changed_fields.append(field_name)

            if changed_fields:
                definition.save(update_fields=changed_fields)
                result.updated_definitions += 1

        if item.get("has_global_value"):
            SettingValue.objects.update_or_create(
                definition=definition,
                scope=SettingScope.GLOBAL,
                user=None,
                defaults={"value": item.get("global_value")},
            )
            result.updated_global_values += 1

        cache.delete(_ck(definition.key, None))
        cache.delete(_is_enabled_ck(definition.key, None))

    return result
