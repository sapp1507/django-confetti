from .swagger_compat import openapi

SETTING_ITEM_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'key':          openapi.Schema(type=openapi.TYPE_STRING, example='key_name', description='Ключ настройки'),
        'category':     openapi.Schema(type=openapi.TYPE_STRING, example='category_name', description='Название категории настройки'),
        'title':        openapi.Schema(type=openapi.TYPE_STRING, example='Название настройки', description='Название настройки'),
        'type':         openapi.Schema(type=openapi.TYPE_STRING, example='bool', description='Тип настройки'),
        'default':      openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='Значение настройки по умолчанию'),
        'global_value': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='Значение настройки глобально'),
        'user_value':   openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='Значение настройки пользователя'),
        'effective':    openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description='Значение настройки, которое будет использовано (user->global->default'),
    },
    required=['key', 'category', 'title', 'type', 'default', '']
)

SETTING_LIST_RESPONSE = openapi.Response(
    description='Список настроек',
    schema=openapi.Schema(
        type=openapi.TYPE_ARRAY,
        items=SETTING_ITEM_SCHEMA
    )
)

SETTING_DETAIL_RESPONSE = openapi.Response(
    description='Одна настройка',
    schema=SETTING_ITEM_SCHEMA
)

ERROR_400 = openapi.Response(description='Неверные данные')
ERROR_401 = openapi.Response(description='Требуется авторизация')
ERROR_403 = openapi.Response(description='Нет доступа')
ERROR_404 = openapi.Response(description='Настройка не найдена')
ERROR_429 = openapi.Response(description='Слишком много запросов')