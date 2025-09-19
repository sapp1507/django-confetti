from typing import Optional, Dict

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status, permissions
from rest_framework.views import APIView

from .api import set_value
from .swagger_compat import swagger_auto_schema
from .swagger_compat import openapi
from .openapi import (SETTING_LIST_RESPONSE, ERROR_429, SETTING_DETAIL_RESPONSE, ERROR_404, ERROR_400, ERROR_401,
                      ERROR_403)
from .models import SettingDefinition, SettingValue, SettingScope
from .serializers import SettingItemSerializer, SettingWriteSerializer
from .conf import confetti_settings


User = get_user_model()


def _resolve(defn: SettingDefinition, user: Optional[User]):
    """Возвращает (global_value, user_value, effective) для одной настройки."""
    gval = SettingValue.objects.filter(
        definition=defn, scope=SettingScope.GLOBAL, user__isnull=True
    ).values_list('value', flat=True).first()

    uval = None
    if user and user.is_authenticated:
        uval = SettingValue.objects.filter(
            definition=defn, scope=SettingScope.USER, user=user
        ).values_list('value', flat=True).first()

    eff = uval if uval is not None else (gval if gval is not None else defn.default)
    return gval, uval, eff

def _defn_dict(defn, user=None) -> Dict:
    gval, uval, eff = _resolve(defn, user)
    return {
        'key': defn.key,
        'category': getattr(defn.category, 'code', None) or getattr(defn.category, 'title', ''),
        'title': defn.title,
        'type': defn.type,
        'default': defn.default,
        'global_value': gval,
        'user_value': uval if user else None,
        'effective': eff if user else (gval if gval is not None else defn.default),
        'frontend': defn.frontend,
    }

class SettingListView(APIView):
    """
    GET /settings/ - список всех настроек.
    - аноним: только глобальные и default
    - Авторизованный: глобальные + его user-override + effective
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return SettingDefinition.objects.select_related('category').all()

    @swagger_auto_schema(
        operation_id='confetti_setting_list',
        operation_description='Возвращает список всех определений настроек.\n\n'
                              '- Аноним: `global_value`, `default`, `effective = global || default`.\n'
                              '- Авторизованный: дополнительно `user_value`, `effective` учитывает override.',
        tags=['confetti'],
        responses={
            200: SETTING_LIST_RESPONSE,
            429: ERROR_429,
        },
    )
    def get(self, request):
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if user and (user.is_staff or user.is_superuser):
            defs = self.get_queryset()
        else:
            defs = self.get_queryset().filter(editable=True)
        items = []
        for d in defs:
            items.append(_defn_dict(d, user))

        return confetti_settings.RESPONSE_METHOD(data=SettingItemSerializer(items, many=True).data)


class SettingFrontendView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_id='confetti_setting_frontend',
        operation_description='Возвращает список всех frontend-настроек.',
        tags=['confetti'],
        responses={
            200: SETTING_LIST_RESPONSE,
            429: ERROR_429,
        },
    )
    def get(self, request):

        cache_frontend = cache.get(f'{confetti_settings.FRONTEND_CACHE_PREFIX}')
        if cache_frontend:
            return confetti_settings.RESPONSE_METHOD(
                data=SettingItemSerializer(cache_frontend, many=True).data)

        defs = SettingDefinition.objects.select_related('category').filter(frontend=True)
        items = []
        for defn in defs:
            items.append(_defn_dict(defn))
        cache.set(confetti_settings.FRONTEND_CACHE_PREFIX, items, confetti_settings.FRONTEND_CACHE_TIMEOUT)
        return confetti_settings.RESPONSE_METHOD(data=SettingItemSerializer(items, many=True).data)



class SettingDetailView(APIView):
    """
    GET /settings/<key>/ - получить одну настройку (анон, пользователь).
    PATCH /settings/<key>/ - изменить:
        - если scope=user или scope не указан -> создаем/обновляем user-override (только авторизованным)
        - если scope=global -> нужен is_staff/is_superuser
    Удалять нельзя - только устанавливать значение (в т.ч. None
    """

    def get_object(self, key: str) -> SettingDefinition | None:
        try:
            if getattr(self.request, 'user', None) and self.request.user.is_superuser:
                return SettingDefinition.objects.select_related('category').get(key=key)
            return SettingDefinition.objects.select_related('category').get(key=key, editable=True)
        except Exception:
            return None

    @swagger_auto_schema(
        operation_id='confetti_setting_detail',
        operation_description='Возвращает одно определение настройки и ее значение для глобального и (если авторизован) текущего пользователя.',
        tags=['confetti'],
        manual_parameters=[
            openapi.Parameter('key', openapi.IN_PATH, description='Ключ настройки', type=openapi.TYPE_STRING)
        ],
        responses={
            200: SETTING_DETAIL_RESPONSE,
            404: ERROR_404,
            429: ERROR_429,
        },
    )
    def get(self, request, key: str):
        defn = self.get_object(key)
        if not defn:
            return confetti_settings.RESPONSE_METHOD(
                data={'message': 'Настройка не найдена'},
                status=status.HTTP_404_NOT_FOUND)

        user = request.user if request.user.is_authenticated else None
        data = _defn_dict(defn, user)
        return confetti_settings.RESPONSE_METHOD(data=SettingItemSerializer(data).data)

    @swagger_auto_schema(
        operation_id='confetti_setting_patch',
        operation_description=(
            'Устанавливает значение настройки.\n\n'
            '- По умолчанию (или `scope=\"user\"`): создает\обновляет пользовательское значение требует авторизацию.'
            '- `scope=\"global\"`: меняет глобальные значения (требует `is_staff` или `is_superuser`).\n'
            '- Удаление запрещено; чтобы вернуть по умолчанию, можно передать `{\"value\"; null}`.'
        ),
        tags=['confetti'],
        manual_parameters=[
            openapi.Parameter('key', openapi.IN_PATH, description='Ключ настройки', type=openapi.TYPE_STRING),
        ],
        request_body=SettingWriteSerializer,
        responses={
            200: SETTING_DETAIL_RESPONSE,
            400: ERROR_400,
            401: ERROR_401,
            403: ERROR_403,
            404: ERROR_404,
            429: ERROR_429,
        },
    )
    def patch(self, request, key: str):
        defn = self.get_object(key)
        if not defn:
            return confetti_settings.RESPONSE_METHOD(
                data={'message': 'Настройка не найдена'},
                status=status.HTTP_404_NOT_FOUND)

        scope = request.data.get('scope')

        # Определяем целевой scope
        if scope == SettingScope.GLOBAL:
            if not (request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
                return confetti_settings.RESPONSE_METHOD(
                    data={'detail': 'Недостаточно прав'},
                    code=status.HTTP_403_FORBIDDEN
                )

            user_for_value = None
            scope_used = SettingScope.GLOBAL
        else:
            if not (request.user and request.user.is_authenticated):
                return confetti_settings.RESPONSE_METHOD(
                    data={'detail': 'Недостаточно прав'},
                    code=status.HTTP_401_UNAUTHORIZED
                )
            user_for_value = request.user
            scope_used = SettingScope.USER

        serializer = SettingWriteSerializer(data=request.data, context={'definition': defn})
        serializer.is_valid(raise_exception=True)

        # sv, _ = SettingValue.objects.get_or_create(
        #     definition=defn,
        #     scope=scope_used,
        #     user=user_for_value if scope_used == SettingScope.USER else None
        # )
        # sv.value = serializer.validated_data['value']
        # sv.save()
        set_value(
            defn.key,
            serializer.validated_data['value'],
            user=user_for_value if scope_used == SettingScope.USER else None,
            scope=scope_used
        )
        return confetti_settings.RESPONSE_METHOD(
            data=SettingItemSerializer(_defn_dict(defn, user_for_value)).data
        )
