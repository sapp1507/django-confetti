import json
import sys

def test_default_response_falls_back_to_json_without_drf(monkeypatch, rf):
    """Тест отсутствия DRF"""
    monkeypatch.setitem(sys.modules, 'rest_framework', None)
    monkeypatch.setitem(sys.modules, 'rest_framework.response', None)
    from confetti.responses import default_response

    resp = default_response(data={'ok': True}, status=201)
    assert resp.status_code == 201
    assert resp['Content-Type'].startswith('application/json')
    assert json.loads(resp.content) == {'ok': True}
