# Запрос на доработку django-confetti: настраиваемый аргумент HTTP-статуса для RESPONSE_METHOD

## Контекст

Мы обновляем `django-confetti` с версии 0.4.2 до 0.5.0 и используем собственный
response factory через настройку:

```python
CONFETTI = {
    'RESPONSE_METHOD': 'utils.responses:success_response',
}
```

Наш callback формирует единый response envelope всего проекта и имеет следующую
сигнатуру:

```python
def success_response(
    data=None,
    detail=None,
    pagination=None,
    code: int = 200,
    status: str = 'success',
):
    return Response(
        {
            'status': status,
            'data': {} if data is None else data,
        },
        status=code,
    )
```

В этом контракте:

- `code` — HTTP status code;
- `status` — строковое поле response body, а не HTTP status code.

Менять этот общий callback специально для Confetti мы не хотим, поскольку он
используется остальным проектом. Создавать project-side wrapper только для
библиотеки также нежелательно: настройка `RESPONSE_METHOD` должна позволять
подключить существующий callback напрямую.

## Проблема в версии 0.5.0

В error responses библиотека вызывает настроенный callback следующим образом:

```python
confetti_settings.RESPONSE_METHOD(
    data={'detail': 'Недостаточно прав'},
    status=status.HTTP_403_FORBIDDEN,
)
```

Такой вызов не приводит к `TypeError`, потому что наш callback имеет аргумент
`status`. Однако значение `403` попадает в JSON body, а HTTP status остаётся
равен значению `code` по умолчанию — `200`.

Фактический результат:

```text
HTTP 200
Content-Type: application/json

{
  "status": 403,
  "data": {
    "detail": "Недостаточно прав"
  }
}
```

Ожидаемый результат с нашим response factory:

```text
HTTP 403
Content-Type: application/json

{
  "status": "success",
  "data": {
    "detail": "Недостаточно прав"
  }
}
```

Название строкового поля `status` и его значение относятся к действующему
контракту нашего проекта. В рамках этой задачи требуется корректно передать
именно HTTP-код через аргумент `code`.

## Требование

Нужно сделать имя аргумента, через который `django-confetti` передаёт HTTP status
code в пользовательский `RESPONSE_METHOD`, явно настраиваемым.

Предлагаемый вариант настройки:

```python
CONFETTI = {
    'RESPONSE_METHOD': 'utils.responses:success_response',
    'RESPONSE_STATUS_KWARG': 'code',
}
```

При такой конфигурации библиотека должна вызывать callback эквивалентно:

```python
success_response(
    data={'detail': 'Недостаточно прав'},
    code=403,
)
```

Если `RESPONSE_STATUS_KWARG` не указан, необходимо сохранить текущий контракт
0.5.0:

```python
CONFETTI = {
    'RESPONSE_METHOD': 'confetti.responses.default_response',
    # RESPONSE_STATUS_KWARG по умолчанию равен 'status'
}
```

То есть default callback библиотеки продолжает получать:

```python
default_response(data=payload, status=403)
```

## Предлагаемая реализация

Желательно централизовать создание всех ответов внутри библиотеки, чтобы views
не вызывали `RESPONSE_METHOD` напрямую.

Пример внутреннего helper:

```python
def build_response(*, data, status=200):
    status_kwarg = confetti_settings.RESPONSE_STATUS_KWARG
    kwargs = {
        'data': data,
        status_kwarg: status,
    }
    return confetti_settings.RESPONSE_METHOD(**kwargs)
```

Defaults:

```python
DEFAULTS = {
    # остальные настройки
    'RESPONSE_STATUS_KWARG': 'status',
}
```

Все REST views должны использовать только этот helper:

```python
return build_response(
    data={'detail': 'Недостаточно прав'},
    status=status.HTTP_403_FORBIDDEN,
)
```

Название helper и конкретная внутренняя архитектура могут отличаться. Важен
внешний конфигурационный контракт и единообразное применение во всех ответах.

## Почему не подходит автоматическое определение по сигнатуре

Не следует выбирать между `status` и `code` только через `inspect.signature`.
Наш callback легально принимает оба аргумента, но они имеют разное назначение:

- `code` управляет HTTP status;
- `status` управляет полем JSON body.

Поэтому выбор должен быть явным и задаваться конфигурацией.

## Обратная совместимость

Ожидается следующее поведение:

1. Пользователи без новой настройки получают прежнее поведение 0.5.0 — HTTP-код
   передаётся как `status`.
2. Пользователи, указавшие `RESPONSE_STATUS_KWARG='code'`, могут напрямую
   подключить callback с HTTP-аргументом `code`.
3. Публичные URL, response payload и default response factory не меняются.
4. Строковый dotted path и callable в `RESPONSE_METHOD` продолжают
   поддерживаться.
5. Настройка применяется ко всем success и error responses, а не только к PATCH.

## Сценарии, которые необходимо проверить

### Default response factory

Конфигурация:

```python
CONFETTI = {}
```

Ожидание:

- успешный запрос возвращает HTTP 200;
- ошибка валидации возвращает HTTP 400;
- отсутствие авторизации возвращает HTTP 401;
- недостаточные права возвращают HTTP 403;
- отсутствующая настройка возвращает HTTP 404.

### Пользовательский callback с аргументом code

Конфигурация:

```python
CONFETTI = {
    'RESPONSE_METHOD': custom_response,
    'RESPONSE_STATUS_KWARG': 'code',
}
```

Callback:

```python
def custom_response(*, data, code=200, status='success'):
    return Response(
        {'status': status, 'data': data},
        status=code,
    )
```

Ожидание:

- callback получает `code=400/401/403/404`;
- callback не получает числовое значение в аргументе `status`;
- фактический HTTP status совпадает с ошибкой;
- поле response body `status` остаётся строкой `success`.

### Строковый dotted path

Та же проверка должна проходить при конфигурации:

```python
CONFETTI = {
    'RESPONSE_METHOD': 'tests.responses:custom_response',
    'RESPONSE_STATUS_KWARG': 'code',
}
```

### Некорректная конфигурация

Желательно валидировать `RESPONSE_STATUS_KWARG` как непустую строку. При
некорректном значении библиотека должна выдавать понятную
`ImproperlyConfigured`, а не скрытую ошибку во время первого REST-запроса.

## Критерии приёмки

- В `CONFETTI` появилась документированная настройка имени HTTP status kwarg.
- Значение по умолчанию сохраняет поведение 0.5.0.
- При `RESPONSE_STATUS_KWARG='code'` наш существующий `success_response`
  подключается напрямую, без wrapper в проекте.
- HTTP-коды 400, 401, 403 и 404 передаются корректно.
- Успешные ответы продолжают возвращать HTTP 200.
- Все места формирования REST response используют единый механизм.
- Есть автоматические тесты для default callback, callable, dotted path и
  пользовательского аргумента `code`.
- README содержит пример настройки с `RESPONSE_STATUS_KWARG='code'`.

## Минимальная конфигурация, которая нужна нашему проекту

После реализации мы хотим использовать библиотеку без дополнительного кода:

```python
CONFETTI = {
    'RESPONSE_METHOD': 'utils.responses:success_response',
    'RESPONSE_STATUS_KWARG': 'code',
    # остальные существующие настройки Confetti
}
```

Это позволит оставить единый response factory проекта и одновременно получать
корректные HTTP status codes из всех endpoint'ов `django-confetti`.
