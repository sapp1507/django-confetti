import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from confetti.admin import SettingDefinitionAdmin, SettingsSnapshotAdmin
from confetti.models import (
    SettingCategory,
    SettingDefinition,
    SettingScope,
    SettingsSnapshot,
    SettingType,
    SettingValue,
)


@pytest.mark.django_db
def test_setting_definition_admin_annotates_values_count():
    category, _ = SettingCategory.objects.get_or_create(code="ui", defaults={"title": "UI"})
    definition = SettingDefinition.objects.create(
        key="ui.theme.admin_test",
        category=category,
        type=SettingType.STR,
        title="Theme",
        description="Color theme for the UI",
    )

    admin_obj = SettingDefinitionAdmin(SettingDefinition, AdminSite())
    request = RequestFactory().get("/admin/confetti/settingdefinition/")

    db_definition = admin_obj.get_queryset(request).get(pk=definition.pk)

    assert admin_obj.values_count(db_definition) == 0
    assert admin_obj.short_description(db_definition) == "Color theme for the UI"


@pytest.mark.django_db
def test_setting_definition_admin_short_description_truncates():
    category, _ = SettingCategory.objects.get_or_create(code="scheduler", defaults={"title": "Scheduler"})
    description = "x" * 150
    definition = SettingDefinition.objects.create(
        key="scheduler.long",
        category=category,
        type=SettingType.STR,
        title="Long description",
        description=description,
    )

    admin_obj = SettingDefinitionAdmin(SettingDefinition, AdminSite())

    short = admin_obj.short_description(definition)

    assert len(short) == 118
    assert short.endswith("…")


def test_settings_snapshot_admin_build_snapshot_diff_detects_full_delta():
    snapshot_payload = [
        {"key": "a", "type": "str", "global_value": "old"},
        {"key": "b", "type": "int", "global_value": 1},
    ]
    current_payload = [
        {"key": "a", "type": "str", "global_value": "new"},
        {"key": "c", "type": "bool", "global_value": True},
    ]

    diff = SettingsSnapshotAdmin._build_snapshot_diff(snapshot_payload, current_payload)

    assert diff["counts"] == {
        "snapshot_total": 2,
        "current_total": 2,
        "only_in_snapshot": 1,
        "only_in_current": 1,
        "changed": 1,
        "unchanged": 0,
    }
    assert diff["only_in_snapshot"] == [{"key": "b", "snapshot": snapshot_payload[1]}]
    assert diff["only_in_current"] == [{"key": "c", "current": current_payload[1]}]
    assert diff["changed"][0]["key"] == "a"
    assert diff["changed"][0]["different_fields"] == ["global_value"]
    assert diff["changed"][0]["snapshot"] == snapshot_payload[0]
    assert diff["changed"][0]["current"] == current_payload[0]
    assert diff["unchanged_keys"] == []


@pytest.mark.django_db
def test_settings_snapshot_admin_comparison_report_contains_snapshot_and_current_states():
    category, _ = SettingCategory.objects.get_or_create(code="ui", defaults={"title": "UI"})
    definition = SettingDefinition.objects.create(
        key="ui.theme.snapshot_admin",
        category=category,
        type=SettingType.STR,
        title="Theme",
    )
    SettingValue.objects.create(
        definition=definition,
        scope=SettingScope.GLOBAL,
        user=None,
        value="light",
    )

    snapshot_payload = [{
        "key": "ui.theme.snapshot_admin",
        "type": "str",
        "title": "Theme",
        "description": "",
        "default": [],
        "choices": [],
        "required": False,
        "enabled": True,
        "editable": True,
        "frontend": False,
        "category": {"code": "ui", "title": "UI"},
        "has_global_value": True,
        "global_value": "dark",
    }]
    snapshot = type("SnapshotObj", (), {"pk": 1, "payload": snapshot_payload})()
    admin_obj = SettingsSnapshotAdmin(SettingsSnapshot, AdminSite())

    rendered = str(admin_obj.comparison_report(snapshot))

    assert "&quot;snapshot&quot;" in rendered
    assert "&quot;current&quot;" in rendered
    assert "&quot;only_in_snapshot&quot;" in rendered
    assert "&quot;only_in_current&quot;" in rendered
    assert "dark" in rendered
    assert "light" in rendered
