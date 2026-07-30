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
    SnapshotValidationError,
    build_global_settings_snapshot_payload,
    preview_global_settings_snapshot_restore,
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


def test_restore_snapshot_creates_missing_settings_and_removes_extra_ones():
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
    assert result.deleted_definitions >= 1
    assert not SettingDefinition.objects.filter(key="feature.extra").exists()
    assert SettingCategory.objects.filter(code="extra").exists()

    restored = SettingDefinition.objects.get(key="feature.missing")
    assert restored.category.code == "restored"

    restored_value = SettingValue.objects.get(
        definition=restored,
        scope=SettingScope.GLOBAL,
        user__isnull=True,
    )
    assert restored_value.value == "configured"


def test_restore_removes_global_value_absent_from_snapshot():
    definition = SettingDefinition.objects.create(
        key='snapshot.remove-global',
        type=SettingType.STR,
        title='Remove global',
        default='fallback',
    )
    SettingValue.objects.create(
        definition=definition,
        scope=SettingScope.GLOBAL,
        value='override',
    )
    payload = build_global_settings_snapshot_payload()
    item = next(entry for entry in payload if entry['key'] == definition.key)
    item['has_global_value'] = False
    item['global_value'] = None

    result = restore_global_settings_snapshot(payload)

    assert result.deleted_global_values == 1
    assert not SettingValue.objects.filter(
        definition__key=definition.key,
        scope=SettingScope.GLOBAL,
        user__isnull=True,
    ).exists()


def test_restore_validates_entire_payload_before_changes():
    before_keys = set(SettingDefinition.objects.values_list('key', flat=True))
    invalid_payload = [{
        'key': 'snapshot.invalid',
        'type': 'unsupported',
        'title': 'Invalid',
    }]

    with pytest.raises(SnapshotValidationError, match='неизвестный тип'):
        restore_global_settings_snapshot(invalid_payload)

    assert set(SettingDefinition.objects.values_list('key', flat=True)) == before_keys


def test_empty_snapshot_requires_explicit_opt_in():
    with pytest.raises(SnapshotValidationError, match='allow_empty'):
        restore_global_settings_snapshot([])

    result = restore_global_settings_snapshot([], dry_run=True, allow_empty=True)

    assert result.deleted_definitions == SettingDefinition.objects.count()
    assert SettingDefinition.objects.exists()


def test_restore_dry_run_returns_preview_without_mutation():
    payload = [{
        'key': 'snapshot.preview-new',
        'type': SettingType.STR,
        'title': 'Preview new',
        'default': 'fallback',
    }]
    before_keys = set(SettingDefinition.objects.values_list('key', flat=True))

    direct_preview = preview_global_settings_snapshot_restore(payload)
    restore_preview = restore_global_settings_snapshot(payload, dry_run=True)

    assert direct_preview == restore_preview
    assert restore_preview.created_definitions == 1
    assert restore_preview.deleted_definitions == len(before_keys)
    assert set(SettingDefinition.objects.values_list('key', flat=True)) == before_keys


def test_restore_rolls_back_all_changes_on_runtime_error(monkeypatch):
    preserved = SettingDefinition.objects.create(
        key='snapshot.preserved-on-error',
        type=SettingType.STR,
        title='Preserved on error',
        default='fallback',
    )
    payload = [{
        'key': 'snapshot.fails-mid-restore',
        'type': SettingType.STR,
        'title': 'Fails mid restore',
        'default': 'fallback',
    }]

    def fail_get_or_create(*args, **kwargs):
        raise RuntimeError('simulated restore failure')

    monkeypatch.setattr(SettingDefinition.objects, 'get_or_create', fail_get_or_create)

    with pytest.raises(RuntimeError, match='simulated restore failure'):
        restore_global_settings_snapshot(payload)

    assert SettingDefinition.objects.filter(pk=preserved.pk).exists()
