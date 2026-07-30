import pytest
from django.urls import reverse

from confetti.api import set_value
from confetti.models import SettingDefinition, SettingScope, SettingValue

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
    assert r.status_code == status.HTTP_200_OK
    # проверим, что пришёл хотя бы наш сид-ключ
    keys = {item['key'] for item in r.json()}
    assert 'feature.jobs' in keys
    assert 'edit' not in keys


def test_list_uses_session_authentication_for_user_override(api_client, user):
    set_value('ui.theme', 'dark', user=user)
    api_client.force_login(user)

    response = api_client.get(reverse('confetti:settings-list'))

    theme = next(item for item in response.json() if item['key'] == 'ui.theme')
    assert theme['user_value'] == 'dark'
    assert theme['effective'] == 'dark'


def test_only_superuser_sees_not_editable_setting_in_list(api_client, django_user_model):
    staff = django_user_model.objects.create_user(
        username='list-staff',
        password='p',
        is_staff=True,
    )
    superuser = django_user_model.objects.create_superuser(
        username='list-superuser',
        password='p',
    )

    api_client.force_authenticate(user=staff)
    staff_keys = {item['key'] for item in api_client.get(reverse('confetti:settings-list')).json()}
    assert 'edit' not in staff_keys

    api_client.force_authenticate(user=superuser)
    superuser_keys = {item['key'] for item in api_client.get(reverse('confetti:settings-list')).json()}
    assert 'edit' in superuser_keys


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
    assert r_patch.status_code == status.HTTP_200_OK,  f'Не изменено по PATCH'
    assert r_patch.json()['user_value'] == 'dark'
    assert r_patch.json()['effective'] == 'dark'

    # null удаляет override и возвращает default
    r_reset = api_client.patch(detail, {'value': None}, format='json')
    assert r_reset.status_code == status.HTTP_200_OK
    assert r_reset.json()['user_value'] is None
    assert r_reset.json()['effective'] == 'light'
    assert not SettingValue.objects.filter(
        definition__key='ui.theme',
        scope=SettingScope.USER,
        user=user,
    ).exists()


def test_patch_global_requires_staff(api_client, user, django_user_model):
    staff = django_user_model.objects.create_user(username='s', password='p', is_staff=True)
    api_client.force_authenticate(user=staff)
    detail = reverse('confetti:settings-detail', kwargs={'key': 'feature.jobs'})
    r = api_client.patch(detail, {'scope': 'global', 'value': False}, format='json')
    assert r.status_code == status.HTTP_200_OK
    assert r.json()['global_value'] is False

    reset = api_client.patch(detail, {'scope': 'global', 'value': None}, format='json')
    assert reset.status_code == status.HTTP_200_OK
    assert reset.json()['global_value'] is None
    assert reset.json()['effective'] is True
    assert not SettingValue.objects.filter(
        definition__key='feature.jobs',
        scope=SettingScope.GLOBAL,
        user__isnull=True,
    ).exists()


def test_patch_user_scope_requires_authentication(api_client):
    detail = reverse('confetti:settings-detail', kwargs={'key': 'feature.jobs'})

    response = api_client.patch(detail, {'value': False}, format='json')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Недостаточно прав'}


def test_patch_global_scope_requires_staff(api_client, user):
    api_client.force_authenticate(user=user)
    detail = reverse('confetti:settings-detail', kwargs={'key': 'feature.jobs'})

    response = api_client.patch(
        detail,
        {'scope': 'global', 'value': False},
        format='json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Недостаточно прав'}


def test_patch_rejects_unknown_scope_before_authentication(api_client):
    detail = reverse('confetti:settings-detail', kwargs={'key': 'feature.jobs'})

    response = api_client.patch(
        detail,
        {'scope': 'organization', 'value': False},
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Недопустимое значение scope'}


def test_patch_reports_invalid_typed_value_as_bad_request(api_client, user):
    api_client.force_authenticate(user=user)
    detail = reverse('confetti:settings-detail', kwargs={'key': 'ui.theme'})

    response = api_client.patch(detail, {'value': 'system'}, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'value' in response.json()


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

    r = api_client.patch(url, {'value': False}, format='json')
    assert r.status_code == status.HTTP_200_OK
    assert r.json()['effective'] is True

    user.is_superuser = False
    user.save()
    api_client.force_authenticate(user=user)
    url = reverse('confetti:settings-detail', kwargs={'key': 'edit'})
    r = api_client.get(url, format='json')
    assert r.status_code == status.HTTP_404_NOT_FOUND

    r = api_client.patch(url, {'value': True}, format='json')
    assert r.status_code == status.HTTP_404_NOT_FOUND


def test_staff_cannot_access_not_editable_setting(api_client, django_user_model):
    staff = django_user_model.objects.create_user(
        username='protected-staff',
        password='p',
        is_staff=True,
    )
    api_client.force_authenticate(user=staff)
    detail = reverse('confetti:settings-detail', kwargs={'key': 'edit'})

    assert api_client.get(detail).status_code == status.HTTP_404_NOT_FOUND
    assert api_client.patch(detail, {'value': True}, format='json').status_code == status.HTTP_404_NOT_FOUND


def test_custom_response_status_kwarg_covers_success_and_view_errors(
    api_client,
    user,
    settings,
):
    settings.CONFETTI = {
        **settings.CONFETTI,
        'RESPONSE_METHOD': 'tests.responses:custom_response',
        'RESPONSE_STATUS_KWARG': 'code',
    }

    success = api_client.get(reverse('confetti:settings-list'))
    assert success.status_code == status.HTTP_200_OK
    assert success.json()['status'] == 'success'
    assert isinstance(success.json()['data'], list)

    detail = reverse('confetti:settings-detail', kwargs={'key': 'ui.theme'})
    api_client.force_authenticate(user=user)
    serializer_error = api_client.patch(
        detail,
        {'value': 'system'},
        format='json',
    )
    assert serializer_error.status_code == status.HTTP_400_BAD_REQUEST
    assert serializer_error.json()['status'] == 'success'
    assert 'value' in serializer_error.json()['data']

    api_client.force_authenticate(user=None)
    unknown_scope = api_client.patch(
        detail,
        {'scope': 'organization', 'value': 'dark'},
        format='json',
    )
    assert unknown_scope.status_code == status.HTTP_400_BAD_REQUEST
    assert unknown_scope.json() == {
        'status': 'success',
        'data': {'detail': 'Недопустимое значение scope'},
    }

    unauthenticated = api_client.patch(detail, {'value': 'dark'}, format='json')
    assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED
    assert unauthenticated.json() == {
        'status': 'success',
        'data': {'detail': 'Недостаточно прав'},
    }

    api_client.force_authenticate(user=user)
    forbidden = api_client.patch(
        detail,
        {'scope': 'global', 'value': 'dark'},
        format='json',
    )
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert forbidden.json() == {
        'status': 'success',
        'data': {'detail': 'Недостаточно прав'},
    }

    missing = reverse('confetti:settings-detail', kwargs={'key': 'missing'})
    not_found_get = api_client.get(missing)
    not_found_patch = api_client.patch(missing, {'value': True}, format='json')

    for response in (not_found_get, not_found_patch):
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            'status': 'success',
            'data': {'message': 'Настройка не найдена'},
        }
