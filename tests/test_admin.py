import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from confetti.admin import SettingDefinitionAdmin
from confetti.models import SettingCategory, SettingDefinition, SettingType


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
