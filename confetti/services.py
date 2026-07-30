from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from django.core.cache import cache
from django.db import transaction

from .api import _ck, _is_enabled_ck
from .models import (
    SettingCategory,
    SettingDefinition,
    SettingScope,
    SettingType,
    SettingValue,
)
from .validators import validate_value


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
    deleted_global_values: int = 0
    deleted_definitions: int = 0


class SnapshotValidationError(ValueError):
    """Snapshot нельзя безопасно применить."""


_SNAPSHOT_DEFAULTS = {
    "description": "",
    "default": None,
    "choices": [],
    "required": False,
    "enabled": True,
    "editable": True,
    "frontend": False,
    "category": None,
    "has_global_value": False,
    "global_value": None,
}


def validate_global_settings_snapshot_payload(
    payload: list[dict[str, Any]],
    *,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    """Проверяет payload целиком и возвращает нормализованную копию."""
    if not isinstance(payload, list):
        raise SnapshotValidationError('Snapshot payload должен быть списком.')
    if not payload and not allow_empty:
        raise SnapshotValidationError(
            'Пустой snapshot запрещён без явного allow_empty=True.'
        )

    normalized_payload = []
    seen_keys = set()
    allowed_types = {value for value, _label in SettingType.choices}

    for index, source_item in enumerate(payload):
        if not isinstance(source_item, dict):
            raise SnapshotValidationError(
                f'Элемент snapshot #{index} должен быть объектом.'
            )

        item = copy.deepcopy(_SNAPSHOT_DEFAULTS)
        item.update(copy.deepcopy(source_item))
        key = item.get('key')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9_.-]+', key):
            raise SnapshotValidationError(
                f'Элемент snapshot #{index} содержит некорректный key.'
            )
        if len(key) > 120:
            raise SnapshotValidationError(f'Ключ {key!r} длиннее 120 символов.')
        if key in seen_keys:
            raise SnapshotValidationError(f'Ключ {key!r} повторяется в snapshot.')
        seen_keys.add(key)

        if item.get('type') not in allowed_types:
            raise SnapshotValidationError(
                f'{key}: неизвестный тип настройки {item.get("type")!r}.'
            )
        if not isinstance(item.get('title'), str) or not item['title']:
            item['title'] = key
        if len(item['title']) > 200:
            raise SnapshotValidationError(f'{key}: title длиннее 200 символов.')
        if not isinstance(item.get('description'), str):
            raise SnapshotValidationError(f'{key}: description должен быть строкой.')

        for field_name in ('required', 'enabled', 'editable', 'frontend'):
            if not isinstance(item.get(field_name), bool):
                raise SnapshotValidationError(
                    f'{key}: поле {field_name} должно быть bool.'
                )

        category = item.get('category')
        if category is not None:
            if not isinstance(category, dict):
                raise SnapshotValidationError(f'{key}: category должен быть объектом или null.')
            code = category.get('code')
            if not isinstance(code, str) or not re.fullmatch(r'[-a-zA-Z0-9_]+', code):
                raise SnapshotValidationError(f'{key}: некорректный category.code.')
            if len(code) > 64:
                raise SnapshotValidationError(f'{key}: category.code длиннее 64 символов.')
            title = category.get('title', code)
            if not isinstance(title, str) or not title or len(title) > 128:
                raise SnapshotValidationError(f'{key}: некорректный category.title.')
            item['category'] = {'code': code, 'title': title}

        if not isinstance(item.get('has_global_value'), bool):
            raise SnapshotValidationError(f'{key}: has_global_value должен быть bool.')
        # Legacy NULL-строка не являлась effective override, поэтому при
        # восстановлении она эквивалентна отсутствующему global value.
        if item['has_global_value'] and item.get('global_value') is None:
            item['has_global_value'] = False

        validation_definition = SettingDefinition(
            key=key,
            type=item['type'],
            title=item['title'],
            choices=item.get('choices'),
            required=item['required'],
            enabled=item['enabled'],
        )
        try:
            if item['type'] == SettingType.CHOICE:
                choices = item.get('choices') or []
                if not isinstance(choices, list) or any(
                    not isinstance(choice, dict) or 'value' not in choice
                    for choice in choices
                ):
                    raise ValueError(
                        'choices должен быть списком объектов с ключом value'
                    )
            if item.get('default') is not None:
                item['default'] = validate_value(validation_definition, item['default'])
            elif item['type'] == SettingType.BOOL:
                item['default'] = item['enabled']
            if item['has_global_value']:
                item['global_value'] = validate_value(
                    validation_definition,
                    item.get('global_value'),
                )
        except (TypeError, ValueError) as exc:
            raise SnapshotValidationError(f'{key}: {exc}') from exc

        if item['required'] and item.get('default') is None and not item['has_global_value']:
            raise SnapshotValidationError(
                f'{key}: required-настройка не имеет default или global value.'
            )

        normalized_payload.append(item)

    return normalized_payload


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


def preview_global_settings_snapshot_restore(
    payload: list[dict[str, Any]],
    *,
    allow_empty: bool = False,
) -> RestoreResult:
    """Возвращает ожидаемые счётчики restore без изменения БД."""
    normalized = validate_global_settings_snapshot_payload(
        payload,
        allow_empty=allow_empty,
    )
    result = RestoreResult()
    snapshot_by_key = {item['key']: item for item in normalized}
    current_by_key = {
        item['key']: item
        for item in build_global_settings_snapshot_payload()
    }

    snapshot_keys = set(snapshot_by_key)
    current_keys = set(current_by_key)
    result.created_definitions = len(snapshot_keys - current_keys)
    result.deleted_definitions = len(current_keys - snapshot_keys)

    existing_categories = {
        category.code: category.title
        for category in SettingCategory.objects.all()
    }
    snapshot_categories = {
        item['category']['code']: item['category']['title']
        for item in normalized
        if item.get('category')
    }
    result.created_categories = len(set(snapshot_categories) - set(existing_categories))
    result.updated_categories = sum(
        existing_categories[code] != title
        for code, title in snapshot_categories.items()
        if code in existing_categories
    )

    for key in snapshot_keys & current_keys:
        expected = snapshot_by_key[key]
        current = current_by_key[key]
        definition_fields = (
            set(SETTING_DEFINITION_SNAPSHOT_FIELDS)
            | {'category'}
        )
        if any(expected.get(field) != current.get(field) for field in definition_fields):
            result.updated_definitions += 1

        if expected['has_global_value']:
            if (
                not current.get('has_global_value')
                or current.get('global_value') != expected.get('global_value')
            ):
                result.updated_global_values += 1
        elif current.get('has_global_value'):
            result.deleted_global_values += 1

    for key in snapshot_keys - current_keys:
        if snapshot_by_key[key]['has_global_value']:
            result.updated_global_values += 1

    return result


@transaction.atomic
def restore_global_settings_snapshot(
    payload: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    allow_empty: bool = False,
) -> RestoreResult:
    normalized = validate_global_settings_snapshot_payload(
        payload,
        allow_empty=allow_empty,
    )
    if dry_run:
        return preview_global_settings_snapshot_restore(
            normalized,
            allow_empty=allow_empty,
        )

    result = RestoreResult()

    snapshot_keys = {
        item["key"]
        for item in normalized
    }
    stale_definitions = SettingDefinition.objects.exclude(key__in=snapshot_keys)

    stale_keys = list(stale_definitions.values_list("key", flat=True))
    result.deleted_definitions = stale_definitions.count()
    stale_definitions.delete()

    for stale_key in stale_keys:
        cache.delete(_ck(stale_key, None))
        cache.delete(_is_enabled_ck(stale_key, None))

    for item in normalized:
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

        global_values = SettingValue.objects.filter(
            definition=definition,
            scope=SettingScope.GLOBAL,
            user=None,
        )
        if item["has_global_value"]:
            existing_global_value = global_values.first()
            if existing_global_value is None:
                SettingValue.objects.create(
                    definition=definition,
                    scope=SettingScope.GLOBAL,
                    user=None,
                    value=item["global_value"],
                )
                result.updated_global_values += 1
            elif existing_global_value.value != item["global_value"]:
                existing_global_value.value = item["global_value"]
                existing_global_value.save(update_fields=["value"])
                result.updated_global_values += 1
        else:
            deleted_count, _ = global_values.delete()
            if deleted_count:
                result.deleted_global_values += 1

        cache.delete(_ck(definition.key, None))
        cache.delete(_is_enabled_ck(definition.key, None))

    return result
