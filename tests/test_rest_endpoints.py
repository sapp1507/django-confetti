import icecream
import pytest
from django.urls import reverse

from confetti.models import SettingDefinition

drf = pytest.importorskip('rest_framework')
from rest_framework.test import APIClient
from rest_framework import status

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_list_settings_anonymous(api_client):
    url = reverse('confetti:settings-list')
    r = api_client.get(url)
    icecream.ic(r)
    assert r.status_code == status.HTTP_200_OK
    # проверим, что пришёл хотя бы наш сид-ключ
    keys = {item['key'] for item in r.json()}
    assert 'feature.jobs' in keys


def test_get_setting_and_patch_user_scope(api_client, user):
    # логинимся сессионо (нам не важно тип аутентификации — просто is_authenticated)
    api_client.force_authenticate(user=user)

    # GET
    detail = reverse('confetti:settings-detail', kwargs={'key': 'ui.theme'})
    r_get = api_client.get(detail)
    assert r_get.status_code == status.HTTP_200_OK, f'Не получено по GET'
    assert r_get.json()['effective'] in ('light', 'dark')

    # PATCH user override
    r_patch = api_client.patch(detail, {'value': 'dark'}, format='json')
    icecream.ic(r_patch.json())
    assert r_patch.status_code == status.HTTP_200_OK,  f'Не изменено по PATCH'
    assert r_patch.json()['user_value'] == 'dark'
    assert r_patch.json()['effective'] == 'dark'


def test_patch_global_requires_staff(api_client, user, django_user_model):
    staff = django_user_model.objects.create_user(username='s', password='p', is_staff=True)
    api_client.force_authenticate(user=staff)
    detail = reverse('confetti:settings-detail', kwargs={'key': 'feature.jobs'})
    r = api_client.patch(detail, {'scope': 'global', 'value': False}, format='json')
    assert r.status_code == status.HTTP_200_OK
    assert r.json()['global_value'] is False


def test_frontend_cache_invalidation(api_client, user):
    url = reverse('confetti:settings-frontend')
    r = api_client.get(url)
    assert r.status_code == status.HTTP_200_OK
    data = r.data
    assert data[0]['key'] == 'front'
    assert data[0]['frontend'] == True
    assert data[0]['default'] == True
    assert data[0]['effective'] == True
    assert len(data) == 1
    defn = SettingDefinition.objects.get(key='front')
    defn.default = False
    defn.save()

    r = api_client.get(url)
    assert r.status_code == status.HTTP_200_OK
    data = r.data
    assert data[0]['key'] == 'front'
    assert data[0]['frontend'] == True
    assert data[0]['default'] == False
    assert data[0]['effective'] == False

def test_user_not_allowed_to_edit_not_editable_settings(api_client, user):
    user.is_superuser = True
    user.save()
    api_client.force_authenticate(user=user)
    url = reverse('confetti:settings-detail', kwargs={'key': 'edit'})
    r = api_client.get(url, format='json')
    assert r.status_code == status.HTTP_200_OK

    r = api_client.patch(url, {'value': True}, format='json')
    assert r.status_code == status.HTTP_200_OK

    user.is_superuser = False
    user.save()
    api_client.force_authenticate(user=user)
    url = reverse('confetti:settings-detail', kwargs={'key': 'edit'})
    r = api_client.get(url, format='json')
    assert r.status_code == status.HTTP_404_NOT_FOUND

    r = api_client.patch(url, {'value': True}, format='json')
    assert r.status_code == status.HTTP_404_NOT_FOUND
