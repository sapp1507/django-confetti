import pytest

from confetti.models import (
    SettingCategory,
    SettingDefinition,
    SettingScope,
    SettingType,
    SettingsSnapshot,
    SettingValue,
)
from confetti.services import (
    build_global_settings_snapshot_payload,
    restore_global_settings_snapshot,
)

pytestmark = pytest.mark.django_db


def test_build_global_settings_snapshot_payload_stores_definition_and_global_value():
    category = SettingCategory.objects.create(code="core", title="Core")
    definition = SettingDefinition.objects.create(
        key="feature.example",
        category=category,
        type=SettingType.BOOL,
        title="Example",
        default=False,
        enabled=True,
        editable=True,
    )
    SettingValue.objects.create(
        definition=definition,
        scope=SettingScope.GLOBAL,
        value=True,
    )

    payload = build_global_settings_snapshot_payload()

    item = next(snapshot_item for snapshot_item in payload if snapshot_item["key"] == "feature.example")
    assert item["key"] == "feature.example"
    assert item["category"]["code"] == "core"
    assert item["global_value"] is True
    assert item["has_global_value"] is True


def test_restore_snapshot_creates_missing_settings_and_does_not_touch_extra_ones():
    extra_category = SettingCategory.objects.create(code="extra", title="Extra")
    SettingDefinition.objects.create(
        key="feature.extra",
        category=extra_category,
        type=SettingType.BOOL,
        title="Extra flag",
        default=False,
    )

    snapshot_payload = [
        {
            "key": "feature.missing",
            "type": SettingType.STR,
            "title": "Missing",
            "description": "new setting",
            "default": "v1",
            "choices": [],
            "required": False,
            "enabled": True,
            "editable": True,
            "frontend": False,
            "category": {"code": "restored", "title": "Restored"},
            "has_global_value": True,
            "global_value": "configured",
        }
    ]
    snapshot = SettingsSnapshot.objects.create(payload=snapshot_payload, comment="restore")

    result = restore_global_settings_snapshot(snapshot.payload)

    assert result.created_definitions == 1
    assert SettingDefinition.objects.filter(key="feature.extra").exists()

    restored = SettingDefinition.objects.get(key="feature.missing")
    assert restored.category.code == "restored"

    restored_value = SettingValue.objects.get(
        definition=restored,
        scope=SettingScope.GLOBAL,
        user__isnull=True,
    )
    assert restored_value.value == "configured"
