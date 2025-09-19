import sys
import types
import pytest

def test_swagger_compat_works_without_drf_yasg(monkeypatch):
    # Симулируем отсутствие drf_yasg
    monkeypatch.setitem(sys.modules, 'drf_yasg', None)
    monkeypatch.setitem(sys.modules, 'drf_yasg.utils', None)
    monkeypatch.setitem(sys.modules, 'drf_yasg.openapi', None)

    from confetti.swagger_compat import swagger_auto_schema, openapi

    @swagger_auto_schema(operation_id='x')  # no-op
    def dummy(x): return x

    assert dummy(1) == 1
    assert hasattr(openapi, 'Schema')
    assert hasattr(openapi, 'Response')
    assert hasattr(openapi, 'Parameter')
