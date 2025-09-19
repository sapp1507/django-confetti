import pytest
from django.core.cache import cache
from django.urls import reverse

from confetti.api import _ck, get, set_value
from confetti.models import SettingDefinition, SettingValue, SettingScope
drf = pytest.importorskip('rest_framework')
from rest_framework.test import APIClient
from rest_framework import status

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

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


def test_cache_frontend(api_client):
    from confetti.defaults import DEFAULTS
    assert cache.get(DEFAULTS['FRONTEND_CACHE_PREFIX'], None) is None
    url = reverse('confetti:settings-frontend')
    r = api_client.get(url)
    assert r.status_code == status.HTTP_200_OK
    cache_data =  cache.get(DEFAULTS['FRONTEND_CACHE_PREFIX'], None)
    assert cache_data is not None
    assert cache_data == r.data