import pytest

from confetti.api import is_enabled
from confetti.models import SettingCategory, SettingDefinition, SettingType


@pytest.mark.django_db
def test_bool_definition_syncs_default_on_create_from_enabled():
    category, _ = SettingCategory.objects.get_or_create(code="flags", defaults={"title": "Flags"})

    definition = SettingDefinition.objects.create(
        key="feature.create-sync",
        category=category,
        type=SettingType.BOOL,
        title="Create sync",
        enabled=False,
        default=True,
    )

    assert definition.default is False


@pytest.mark.django_db
def test_bool_definition_syncs_default_when_enabled_toggles():
    category, _ = SettingCategory.objects.get_or_create(code="flags", defaults={"title": "Flags"})
    definition = SettingDefinition.objects.create(
        key="feature.toggle-sync",
        category=category,
        type=SettingType.BOOL,
        title="Toggle sync",
        enabled=True,
        default=True,
    )
    assert definition.default is True

    definition.enabled = False
    definition.save()
    definition.refresh_from_db()

    assert definition.default is False

    definition.enabled = True
    definition.save()
    definition.refresh_from_db()

    assert definition.default is True


@pytest.mark.django_db
def test_is_enabled_uses_bool_enabled_instead_of_stale_default():
    category, _ = SettingCategory.objects.get_or_create(code="flags", defaults={"title": "Flags"})
    definition = SettingDefinition.objects.create(
        key="feature.enabled-source",
        category=category,
        type=SettingType.BOOL,
        title="Enabled source",
        enabled=True,
        default=True,
    )

    # Имитируем старые или вручную обновлённые данные с нарушенной
    # синхронизацией, чтобы проверить источник истины в публичном API.
    SettingDefinition.objects.filter(pk=definition.pk).update(default=False)

    assert is_enabled(definition.key) is True
