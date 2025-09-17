import pytest
from confetti.api import get, set_value
from confetti.models import SettingScope, SettingDefinition
from django.core.cache import cache

pytestmark = pytest.mark.django_db


def test_get_returns_default_when_no_values():
    # из сид-данных: ui.theme default=light
    assert get("ui.theme") == "light"


def test_global_then_user_override_precedence(user):
    # глобально переопределим
    set_value("ui.theme", "dark", scope=SettingScope.GLOBAL)
    assert get("ui.theme") == "dark"

    # для пользователя — персональное значение
    set_value("ui.theme", "light", user=user)
    assert get("ui.theme", user=user) == "light"     # юзер имеет приоритет
    assert get("ui.theme") == "dark"                  # глобально осталось dark


def test_cache_invalidation_on_set(user):
    # установим и попадём в кэш
    set_value("feature.jobs", True, scope=SettingScope.GLOBAL)
    assert get("feature.jobs") is True

    # теперь изменим значение → должно обновиться
    set_value("feature.jobs", False, scope=SettingScope.GLOBAL)
    assert get("feature.jobs") is False
