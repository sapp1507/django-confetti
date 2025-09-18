import pytest
from confetti.api import get, set_value
from confetti.models import SettingScope, SettingDefinition
from django.core.cache import cache
from icecream import ic

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


def test_cache_invalidation_on_set(user):
    """Простое изменение значений. проверка сброса кэш."""

    set_value('feature.jobs', True, scope=SettingScope.GLOBAL)
    assert get('feature.jobs') is True

    # теперь изменим значение → должно обновиться
    set_value('feature.jobs', False, scope=SettingScope.GLOBAL)
    assert get('feature.jobs') is False

def test_edit_not_editable(user):
    """Проверяет что нельзя изменить не редактируемую настройку."""
    assert get('edit') == False

    dfn = ic(SettingDefinition.objects.get(key='edit'))
    assert dfn.editable is False

    set_value('edit', True)
    dfn = SettingDefinition.objects.get(key='edit')
    assert dfn.editable is False
    assert get('edit') == False
