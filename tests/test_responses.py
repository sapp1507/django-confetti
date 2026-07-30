import json
import sys

import pytest
from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings


def test_build_response_uses_default_status_kwarg():
    from confetti.responses import build_response

    response = build_response(data={'ok': True}, status=201)

    assert response.status_code == 201
    assert response.data == {'ok': True}


def test_build_response_uses_configured_status_kwarg_for_callable():
    calls = []

    def custom_response(*, data, code=200, status='success', **kwargs):
        calls.append({
            'data': data,
            'code': code,
            'status': status,
            'kwargs': kwargs,
        })
        from rest_framework.response import Response
        return Response({'status': status, 'data': data}, status=code)

    with override_settings(CONFETTI={
        'RESPONSE_METHOD': custom_response,
        'RESPONSE_STATUS_KWARG': 'code',
    }):
        from confetti.responses import build_response
        response = build_response(data={'detail': 'error'}, status=403)

    assert response.status_code == 403
    assert response.data == {'status': 'success', 'data': {'detail': 'error'}}
    assert calls == [{
        'data': {'detail': 'error'},
        'code': 403,
        'status': 'success',
        'kwargs': {},
    }]


@pytest.mark.parametrize('response_method', [
    'tests.responses.custom_response',
    'tests.responses:custom_response',
])
def test_build_response_supports_dotted_response_method(response_method):
    with override_settings(CONFETTI={
        'RESPONSE_METHOD': response_method,
        'RESPONSE_STATUS_KWARG': 'code',
    }):
        from confetti.responses import build_response
        response = build_response(data={'ok': True}, status=202)

    assert response.status_code == 202
    assert response.data == {'status': 'success', 'data': {'ok': True}}


def test_response_settings_cache_reloads_after_override():
    from confetti.responses import build_response

    first = build_response(data={'first': True}, status=201)
    assert first.status_code == 201
    assert first.data == {'first': True}

    with override_settings(CONFETTI={
        'RESPONSE_METHOD': 'tests.responses:custom_response',
        'RESPONSE_STATUS_KWARG': 'code',
    }):
        second = build_response(data={'second': True}, status=202)

    third = build_response(data={'third': True}, status=203)

    assert second.status_code == 202
    assert second.data == {'status': 'success', 'data': {'second': True}}
    assert third.status_code == 203
    assert third.data == {'third': True}


@pytest.mark.parametrize('status_kwarg', [None, '', '   ', 'data'])
def test_build_response_rejects_invalid_status_kwarg(status_kwarg):
    with override_settings(CONFETTI={
        'RESPONSE_METHOD': 'tests.responses:custom_response',
        'RESPONSE_STATUS_KWARG': status_kwarg,
    }):
        from confetti.responses import build_response

        with pytest.raises(ImproperlyConfigured, match='RESPONSE_STATUS_KWARG'):
            build_response(data={'ok': False}, status=400)


def test_invalid_status_kwarg_is_reported_by_django_system_check():
    with override_settings(CONFETTI={'RESPONSE_STATUS_KWARG': 'data'}):
        errors = [error for error in run_checks() if error.id == 'confetti.E001']

    assert len(errors) == 1
    assert errors[0].id == 'confetti.E001'
    assert 'RESPONSE_STATUS_KWARG' in errors[0].msg


def test_default_response_falls_back_to_json_without_drf(monkeypatch, rf):
    """Тест отсутствия DRF"""
    monkeypatch.setitem(sys.modules, 'rest_framework', None)
    monkeypatch.setitem(sys.modules, 'rest_framework.response', None)
    from confetti.responses import default_response

    resp = default_response(data={'ok': True}, status=201)
    assert resp.status_code == 201
    assert resp['Content-Type'].startswith('application/json')
    assert json.loads(resp.content) == {'ok': True}
