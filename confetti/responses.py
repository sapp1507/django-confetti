from  __future__ import annotations
from typing import Any
from django.http import JsonResponse

def default_response(*, data: Any, status: int = 200):
    """
    Универсальный ответ:
    - если DRF установлен - используем rest-framework.response.Response
    - иначе - Django JsonResponse
    """
    try:
        from rest_framework.response import Response
        return Response(data=data, status=status)
    except Exception:
        safe = isinstance(data, (dict, list))
        return JsonResponse(data, status=status, safe=safe, json_dumps_params={'ensure_ascii': False})