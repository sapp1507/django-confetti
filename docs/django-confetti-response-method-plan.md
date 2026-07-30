# План доработки настраиваемого HTTP status kwarg для RESPONSE_METHOD

Дата анализа: 2026-07-30.

Статус: выполнено 2026-07-30. Добавлены настройка
`RESPONSE_STATUS_KWARG`, единый `build_response`, runtime-валидация и Django
system check; все локальные ответы REST views переведены на helper. Полный
набор из 93 тестов проходит, Django check чистый, изменений моделей и миграций
нет.

Основание: запрос
[`django-confetti-response-method-requirement.md`](django-confetti-response-method-requirement.md)
и состояние репозитория на commit `f501711` (`django-confetti` 0.5.0).

## Цель

Добавить в `settings.CONFETTI` настройку `RESPONSE_STATUS_KWARG`, которая
определяет имя именованного аргумента для передачи HTTP status code в
пользовательский `RESPONSE_METHOD`.

Новый контракт:

```python
CONFETTI = {
    'RESPONSE_METHOD': 'utils.responses:success_response',
    'RESPONSE_STATUS_KWARG': 'code',
}
```

должен приводить к вызову, эквивалентному:

```python
success_response(data=payload, code=403)
```

Без новой настройки поведение версии 0.5.0 сохраняется: HTTP-код передаётся
через `status`, а встроенный `default_response` продолжает работать без
изменений.

## Что обнаружено в текущей реализации

- `confetti/defaults.py` содержит `RESPONSE_METHOD`, но не содержит настройки
  имени status kwarg.
- `confetti/conf.py` уже поддерживает callable, dotted path через точку и
  вариант `module:callable`, а также очищает кэш настроек по сигналу
  `setting_changed`. Этот механизм следует сохранить.
- В `confetti/views.py` находится 11 прямых вызовов
  `confetti_settings.RESPONSE_METHOD`: 5 успешных ответов и 6 вручную
  сформированных ошибок 400/401/403/404.
- Успешные ответы сейчас полагаются на значение HTTP 200 по умолчанию в
  callback, а ошибки явно передают `status=`. После централизации helper должен
  явно передавать и 200, чтобы новая настройка одинаково применялась к success
  и error responses.
- Ошибка `SettingWriteSerializer` сейчас создаётся через
  `is_valid(raise_exception=True)`. Её обрабатывает DRF, поэтому эта ветка
  обходит пользовательский `RESPONSE_METHOD`. Для заявленного сценария HTTP
  400 её необходимо формировать через общий helper.
- Ответы, которые генерирует сам DRF до или вне тела view (например, parse
  error, 405 Method Not Allowed и throttling 429), сейчас также не проходят
  через `RESPONSE_METHOD`. Их глобальная обёртка потребовала бы отдельного
  exception handler/mixin, изменила бы существующие payload и выходит за
  минимальный контракт этой доработки.

## Проектное решение

### 1. Новая настройка с совместимым default

В `confetti/defaults.py` добавить:

```python
'RESPONSE_STATUS_KWARG': 'status',
```

Default намеренно совпадает с текущей сигнатурой
`confetti.responses.default_response(*, data, status=200)`. Сигнатуру
встроенной фабрики менять не нужно.

Не следует определять имя аргумента через `inspect.signature`: callback может
легально принимать одновременно `code` и `status` с разной семантикой.

### 2. Единая внутренняя функция создания ответа

В `confetti/responses.py` добавить внутренний или публично не обещанный helper,
например:

```python
def build_response(*, data: Any, status: int = 200):
    status_kwarg = confetti_settings.RESPONSE_STATUS_KWARG
    return confetti_settings.RESPONSE_METHOD(
        **{'data': data, status_kwarg: status}
    )
```

Импорт `confetti_settings` желательно сделать внутри helper либо отдельно
проверить отсутствие цикла `conf.py -> import_string(RESPONSE_METHOD) ->
responses.py -> conf.py` при первом разрешении default callback.

Параметр `status` в сигнатуре helper является внутренним нормализованным
понятием и не зависит от имени аргумента внешнего callback. Helper не должен
менять payload, перехватывать исключения callback или пытаться повторить вызов
с другим именем аргумента: ошибки интеграции должны оставаться явными.

### 3. Валидация конфигурации

`RESPONSE_STATUS_KWARG` необходимо принимать только как непустую строку.
Дополнительно следует отклонять значение `data`, поскольку при построении
словаря kwargs оно конфликтует с обязательным аргументом payload. Рекомендуемое
сообщение:

```text
CONFETTI['RESPONSE_STATUS_KWARG'] must be a non-empty string other than 'data'.
```

При runtime-доступе ошибка должна иметь тип
`django.core.exceptions.ImproperlyConfigured`, а не проявляться позднее как
`TypeError` или как вызов строкового значения. Валидацию следует держать в
одной функции и использовать:

- при получении значения helper-ом;
- в зарегистрированной Django system check, чтобы `manage.py check` заранее
  показывал некорректную конфигурацию.

Не нужно проверять наличие выбранного параметра в сигнатуре callback: callback
может использовать `**kwargs`, декоратор или объект с `__call__`, а явный выбор
пользователя является частью контракта.

### 4. Перевод REST views на helper

В `confetti/views.py` заменить все 11 прямых вызовов `RESPONSE_METHOD` на
`build_response`:

- список настроек — 200;
- frontend list, включая cache hit и cache miss — 200;
- detail GET — 200 и 404;
- detail PATCH — 200, 400, 401, 403 и 404.

Прямых вызовов `confetti_settings.RESPONSE_METHOD` во views после изменения
остаться не должно. Это следует закрепить обзором кода; отдельный тест на текст
исходника не нужен.

Для ошибки сериализатора заменить `is_valid(raise_exception=True)` на явную
ветку:

```python
if not serializer.is_valid():
    return build_response(
        data=serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )
```

Это сохраняет существующую структуру validation payload, но гарантирует вызов
настроенной фабрики и корректную передачу `code=400`.

### 5. Явная граница охвата

В рамках этой доработки `RESPONSE_METHOD` применяется ко всем ответам, которые
формируют REST views библиотеки, включая локальную serializer validation.
Глобально перехватывать ответы DRF 400/401/403/405/429, возникшие до входа во
view или в инфраструктуре DRF, не следует: для этого нужен отдельный публичный
контракт exception handling и решение о преобразовании чужого payload.

Если под фразой «все success и error responses» подразумеваются также такие
framework-generated ответы, это нужно вынести во второй этап и предварительно
согласовать:

- должен ли пользовательский callback оборачивать исходный `exc.detail`;
- как избежать двойной обработки уже построенных response;
- сохраняются ли стандартные DRF headers (`Allow`, `WWW-Authenticate`,
  `Retry-After`);
- распространяется ли настройка только на Confetti views или на весь проект.

## План тестирования

### Unit-тесты helper и конфигурации

В `tests/test_responses.py` добавить проверки:

1. Без пользовательской настройки helper вызывает default factory с
   `status=201` и возвращает фактический HTTP 201.
2. Callable с `RESPONSE_STATUS_KWARG='code'` получает `data` и `code`, при этом
   его body-параметр `status='success'` не перезаписывается числом.
3. Dotted path с точкой разрешается и получает `code`.
4. Dotted path с двоеточием продолжает разрешаться и получает `code`.
5. После `override_settings(CONFETTI=...)` кэш `confetti_settings` не сохраняет
   предыдущее значение status kwarg или response factory.
6. `None`, пустая строка и `data` для `RESPONSE_STATUS_KWARG` приводят к
   понятной `ImproperlyConfigured`.
7. Callback с `**kwargs` поддерживается без анализа сигнатуры.

Тестовый callback для dotted path разместить в импортируемом модуле, например
`tests/responses.py`, чтобы проверять реальный механизм `import_string`, а не
подменять его mock-ом.

### Интеграционные тесты REST API

В `tests/test_rest_endpoints.py` под конфигурацией custom callback +
`RESPONSE_STATUS_KWARG='code'` проверить следующие ветки:

| Сценарий | Ожидаемый HTTP-код | Проверяемый путь |
|---|---:|---|
| list/detail success | 200 | success также проходит через `code` |
| невалидное значение serializer | 400 | больше не обходит factory |
| неизвестный scope | 400 | ручная validation branch |
| анонимный user PATCH | 401 | authentication branch view |
| user выполняет global PATCH | 403 | permission branch view |
| отсутствующая настройка | 404 | GET и PATCH |

Для каждого error response проверить одновременно:

- фактический `response.status_code`;
- callback получил числовое значение именно в `code`;
- поле body `status` осталось строкой `'success'`;
- исходный `data` payload не изменился.

Существующие тесты default factory должны остаться зелёными и тем самым
закрепить обратную совместимость для HTTP 200/400/401/403/404.

### Общая регрессия

После реализации выполнить:

```bash
pytest -q
python manage.py check
python manage.py makemigrations --check --dry-run
```

Изменений моделей и новой миграции эта доработка не требует.

## Документация и выпуск

- В секции конфигурации `README.md` добавить
  `"RESPONSE_STATUS_KWARG": "status"` и пример callback с `code`.
- Явно описать, что настройка задаёт имя аргумента HTTP-кода, а не поле JSON
  body, и что значение по умолчанию — `status`.
- Указать поддержку callable, `module.callable` и `module:callable` для
  `RESPONSE_METHOD`.
- Добавить запись в `CHANGELOG.md` для следующего выпуска без изменения
  payload/URL default-конфигурации.
- Версию пакета определять в рамках подготовки выпуска; сама реализация не
  должна произвольно менять `pyproject.toml`.

## Рекомендуемая последовательность реализации

1. Добавить тестовые callback и падающие unit-тесты нового контракта.
2. Добавить default, валидатор и `build_response`.
3. Перевести все ручные ответы views на helper.
4. Перевести serializer validation на явный ответ через helper.
5. Добавить интеграционную матрицу 200/400/401/403/404 для custom callback.
6. Добавить system check и тесты некорректной конфигурации.
7. Обновить README и changelog.
8. Выполнить полную регрессию, Django check и проверку отсутствия миграций.

## Критерии готовности

- `RESPONSE_STATUS_KWARG` документирован и по умолчанию равен `status`.
- Существующий callback с HTTP-аргументом `code` подключается напрямую без
  дополнительной обёртки на стороне проекта.
- Callable и оба поддерживаемых формата dotted path продолжают работать.
- Все вручную сформированные Confetti responses используют единый helper.
- В custom-конфигурации HTTP 200/400/401/403/404 передаются через `code`, а
  строковое поле body `status` не повреждается.
- Default factory сохраняет payload и HTTP-поведение версии 0.5.0.
- Некорректный status kwarg диагностируется как `ImproperlyConfigured` и через
  Django system check.
- Полный набор тестов проходит, `manage.py check` чистый, миграции не создаются.
