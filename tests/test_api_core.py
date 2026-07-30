import pytest
from confetti.api import get, is_enabled, set_value
from confetti.models import SettingDefinition, SettingScope, SettingType, SettingValue
from django.core.cache import cache

pytestmark = pytest.mark.django_db


def test_get_returns_default_when_no_values():
    """Проверяет получение настройки."""

    assert get('ui.theme') == 'light'


def test_global_then_user_override_precedence(user):
    """Проверяет изменение user настроек, и что не трогает global."""

    set_value('ui.theme', 'dark', scope=SettingScope.GLOBAL)
    assert get('ui.theme') == 'dark', f'Не сменилось глобальное значение {get("ui.theme")} != dark'

    set_value('ui.theme', 'light', user=user)
    assert get('ui.theme', user=user) == 'light', f'У user не сменилось значение {get("ui.theme", user=user)} != light'
    assert get('ui.theme') == 'dark', f'Глобальная настройка изменилась {get("ui.theme")} != dark'


def test_none_removes_user_and_global_overrides(user):
    set_value('ui.theme', 'dark', scope=SettingScope.GLOBAL)
    set_value('ui.theme', 'light', user=user)

    assert set_value('ui.theme', None, user=user) is None
    assert get('ui.theme', user=user) == 'dark'
    assert not SettingValue.objects.filter(
        definition__key='ui.theme',
        scope=SettingScope.USER,
        user=user,
    ).exists()

    assert set_value('ui.theme', None, scope=SettingScope.GLOBAL) is None
    assert get('ui.theme', user=user) == 'light'
    assert not SettingValue.objects.filter(
        definition__key='ui.theme',
        scope=SettingScope.GLOBAL,
        user__isnull=True,
    ).exists()


def test_user_scope_requires_user():
    with pytest.raises(ValueError, match='пользователя'):
        set_value('ui.theme', 'dark', scope=SettingScope.USER)


def test_set_value_rejects_unknown_scope():
    with pytest.raises(ValueError, match='scope'):
        set_value('ui.theme', 'dark', scope='organization')


def test_required_override_cannot_be_removed_without_fallback():
    SettingDefinition.objects.create(
        key='required.without-fallback',
        type=SettingType.STR,
        title='Required without fallback',
        default=None,
        required=True,
    )

    with pytest.raises(ValueError, match='fallback'):
        set_value('required.without-fallback', None, scope=SettingScope.GLOBAL)


def test_cache_invalidation_on_set(user):
    """Простое изменение значений. проверка сброса кэш."""

    set_value('feature.jobs', True, scope=SettingScope.GLOBAL)
    assert get('feature.jobs') is True

    # теперь изменим значение → должно обновиться
    set_value('feature.jobs', False, scope=SettingScope.GLOBAL)
    assert get('feature.jobs') is False

def test_bool_enabled_is_source_of_truth_for_not_editable_setting(user):
    """Bool использует enabled, а protected-настройка не принимает override."""
    assert get('edit') is True
    assert is_enabled('edit') is True

    dfn = SettingDefinition.objects.get(key='edit')
    assert dfn.editable is False
    assert dfn.enabled is True
    assert dfn.default is True

    set_value('edit', False)
    dfn = SettingDefinition.objects.get(key='edit')
    assert dfn.editable is False
    assert get('edit') is True
    assert is_enabled('edit') is True
