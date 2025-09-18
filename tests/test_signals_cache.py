import pytest
from django.core.cache import cache
from confetti.api import _ck, get, set_value
from confetti.models import SettingDefinition, SettingValue, SettingScope

pytestmark = pytest.mark.django_db


def test_signals_invalidate_cache_for_user_and_global(user):
    # подготовка: выставим оба значения
    set_value('ui.theme', 'dark', scope=SettingScope.GLOBAL)
    set_value('ui.theme', 'light', user=user)

    # прогреть кэш
    assert get('ui.theme') == 'dark'
    assert get('ui.theme', user=user) == 'light'

    # вручную удалить user value → сигнал post_delete должен вычистить кэш-ключ пользователя
    sv_user = SettingValue.objects.get(definition__key='ui.theme', scope=SettingScope.USER, user=user)
    cache_key_user = _ck('ui.theme', user.id)
    assert cache.get(cache_key_user) is not None

    sv_user.delete()
    assert cache.get(cache_key_user) is None  # кэш инвалидирован
    # теперь эффективное для юзера станет "dark" (глобальное)
    assert get('ui.theme', user=user) == 'dark'

    # обновим глобальное → сигнал должен вычистить глобальный кэш
    set_value('ui.theme', 'light', scope=SettingScope.GLOBAL)
    assert get('ui.theme') == 'light'
