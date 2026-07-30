import pytest
from django.core.cache import cache
from django.urls import reverse

from confetti.api import _ck, get, is_enabled, set_value
from confetti.conf import confetti_settings
from confetti.models import SettingDefinition, SettingScope, SettingValue
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


def test_global_change_invalidates_is_enabled_fallback_for_user(user):
    assert is_enabled('feature.jobs', user=user) is True

    set_value('feature.jobs', False, scope=SettingScope.GLOBAL)

    assert is_enabled('feature.jobs', user=user) is False


def test_user_is_enabled_override_survives_unrelated_global_change(user):
    set_value('feature.jobs', False, user=user)
    assert is_enabled('feature.jobs', user=user) is False

    set_value('feature.jobs', True, scope=SettingScope.GLOBAL)

    assert is_enabled('feature.jobs', user=user) is False


def test_definition_disable_invalidates_cached_user_override(user):
    set_value('feature.jobs', True, user=user)
    assert is_enabled('feature.jobs', user=user) is True

    definition = SettingDefinition.objects.get(key='feature.jobs')
    definition.enabled = False
    definition.save()

    assert is_enabled('feature.jobs', user=user) is False


def test_global_override_delete_invalidates_user_fallback(user):
    set_value('feature.jobs', False, scope=SettingScope.GLOBAL)
    assert is_enabled('feature.jobs', user=user) is False

    set_value('feature.jobs', None, scope=SettingScope.GLOBAL)

    assert is_enabled('feature.jobs', user=user) is True


def test_missing_flag_does_not_cache_caller_default():
    assert is_enabled('missing.flag', default=False) is False
    assert is_enabled('missing.flag', default=True) is True


def test_global_frontend_value_change_invalidates_frontend_cache(api_client):
    url = reverse('confetti:settings-frontend')
    initial = api_client.get(url)
    assert initial.status_code == status.HTTP_200_OK
    assert initial.json()[0]['effective'] is True

    set_value('front', False, scope=SettingScope.GLOBAL)

    updated = api_client.get(url)
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()[0]['effective'] is False


def test_disabling_frontend_flag_removes_it_from_cached_response(api_client):
    url = reverse('confetti:settings-frontend')
    assert [item['key'] for item in api_client.get(url).json()] == ['front']

    definition = SettingDefinition.objects.get(key='front')
    definition.frontend = False
    definition.save(update_fields=['frontend'])

    assert api_client.get(url).json() == []


def test_empty_frontend_response_is_cached(api_client):
    SettingDefinition.objects.filter(frontend=True).update(frontend=False)
    cache.delete(confetti_settings.FRONTEND_CACHE_PREFIX)

    response = api_client.get(reverse('confetti:settings-frontend'))

    assert response.json() == []
    assert cache.get(confetti_settings.FRONTEND_CACHE_PREFIX, 'missing') == []
