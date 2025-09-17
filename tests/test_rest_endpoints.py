import pytest
from django.urls import reverse

drf = pytest.importorskip("rest_framework")
from rest_framework.test import APIClient
from rest_framework import status

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_list_settings_anonymous(api_client):
    url = reverse("confetti:settings-list")
    r = api_client.get(url)
    assert r.status_code == status.HTTP_200_OK
    # проверим, что пришёл хотя бы наш сид-ключ
    keys = {item["key"] for item in r.json()}
    assert "feature.jobs" in keys


def test_get_setting_and_patch_user_scope(api_client, user):
    # логинимся сессионо (нам не важно тип аутентификации — просто is_authenticated)
    api_client.force_authenticate(user=user)

    # GET
    detail = reverse("confetti:settings-detail", kwargs={"key": "ui.theme"})
    r_get = api_client.get(detail)
    assert r_get.status_code == status.HTTP_200_OK
    assert r_get.json()["effective"] in ("light", "dark")

    # PATCH user override
    r_patch = api_client.patch(detail, {"value": "dark"}, format="json")
    assert r_patch.status_code == status.HTTP_200_OK
    assert r_patch.json()["user_value"] == "dark"
    assert r_patch.json()["effective"] == "dark"


def test_patch_global_requires_staff(api_client, user, django_user_model):
    staff = django_user_model.objects.create_user(username="s", password="p", is_staff=True)
    api_client.force_authenticate(user=staff)
    detail = reverse("confetti:settings-detail", kwargs={"key": "feature.jobs"})
    r = api_client.patch(detail, {"scope": "global", "value": False}, format="json")
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["global_value"] is False
