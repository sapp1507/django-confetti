from __future__ import annotations

try:
    from drf_yasg.utils import swagger_auto_schema as _swagger_auto_schema
    from drf_yasg import openapi as _openapi
    DRF_YASG_AVAILABLE = True
except Exception:
    DRF_YASG_AVAILABLE = False
    _swagger_auto_schema = None
    _openapi = None


def swagger_auto_schema(*arfs, **kwargs):
    """Ноу-оп декоратор, если drf-yasg отсутствует."""
    if not DRF_YASG_AVAILABLE:
        def _decorator(view):
            return view
        return _decorator
    return _swagger_auto_schema(*arfs, **kwargs)

class openapi:
    if DRF_YASG_AVAILABLE:
        Schema = _openapi.Schema
        Response = _openapi.Response
        Parameter = _openapi.Parameter
        TYPE_OBJECT = _openapi.TYPE_OBJECT
        TYPE_ARRAY = _openapi.TYPE_ARRAY
        TYPE_STRING = _openapi.TYPE_STRING
        IN_PATH = _openapi.IN_PATH
    else:
        TYPE_OBJECT = 'object'
        TYPE_ARRAY = 'array'
        TYPE_STRING = 'string'
        IN_PATH = 'path'

        class Schema:
            def __init__(self, **kwargs): pass

        class Response:
            def __init__(self, *args, **kwargs): pass

        class Parameter:
            def __init__(self, *args, **kwargs): pass
