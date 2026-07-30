import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured


def test_core_modules_import_without_drf_or_icecream(monkeypatch):
    monkeypatch.setitem(sys.modules, 'rest_framework', None)
    monkeypatch.setitem(sys.modules, 'rest_framework.response', None)
    monkeypatch.setitem(sys.modules, 'icecream', None)

    responses = importlib.reload(importlib.import_module('confetti.responses'))
    api = importlib.reload(importlib.import_module('confetti.api'))

    assert callable(responses.default_response)
    assert callable(api.get)
    assert callable(api.set_value)
    assert callable(api.is_enabled)


def test_urls_explain_how_to_install_missing_drf(monkeypatch):
    monkeypatch.setitem(sys.modules, 'rest_framework', None)
    monkeypatch.delitem(sys.modules, 'confetti.views', raising=False)
    monkeypatch.delitem(sys.modules, 'confetti.urls', raising=False)

    with pytest.raises(ImproperlyConfigured, match=r'django-confetti\[drf\]'):
        importlib.import_module('confetti.urls')
