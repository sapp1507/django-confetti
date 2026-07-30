# Django Confetti 🎉

`django-confetti` — Django-приложение для настроек и feature flags, значения
которых хранятся в БД. Настройка может иметь default, глобальный override и
override конкретного пользователя.

Приоритет вычисления значения:

```text
user override → global override → definition default → caller default
```

## Возможности

- типизированный реестр настроек и категории;
- глобальные и пользовательские overrides;
- отдельная семантика bool-переключателей через `enabled`;
- кэширование и автоматическая инвалидация через Django signals;
- seed/sync из `settings.CONFETTI`;
- optional REST API на Django REST Framework;
- optional Swagger-аннотации через drf-yasg;
- Django Admin для definitions, values и snapshots;
- атомарное восстановление snapshots с validation и dry-run.

## Требования и установка

- Python 3.10+;
- Django 3.2+;
- Django REST Framework 3.14+ для REST API;
- drf-yasg 1.21.5+ для Swagger-аннотаций.

Только основной Python API:

```bash
pip install django-confetti
```

С REST API:

```bash
pip install django-confetti[drf]
```

С REST API и Swagger:

```bash
pip install django-confetti[docs]
```

Добавьте приложение:

```python
INSTALLED_APPS = [
    # ...
    "confetti",
]
```

Примените миграции:

```bash
python manage.py migrate
```

## Конфигурация

Настройки задаются в `settings.CONFETTI`. Все ключи необязательны:

```python
CONFETTI = {
    "CACHE_PREFIX": "confetti:v1",
    "FRONTEND_CACHE_PREFIX": "confetti:v1:frontend",
    "FRONTEND_CACHE_TIMEOUT": 300,
    "RESPONSE_METHOD": "confetti.responses.default_response",
    "AUTO_SEED": True,
    "SEED_CATEGORIES": [
        {"code": "notifications", "title": "Уведомления"},
        {"code": "ui", "title": "Интерфейс"},
    ],
    "SEED_DEFINITIONS": [
        {
            "key": "notifications.email.enabled",
            "type": "bool",
            "category": "notifications",
            "title": "Почтовые уведомления",
            "enabled": True,
            "editable": True,
            "frontend": False,
        },
        {
            "key": "ui.theme",
            "type": "choice",
            "category": "ui",
            "title": "Тема интерфейса",
            "default": "light",
            "choices": [
                {"value": "light", "label": "Светлая"},
                {"value": "dark", "label": "Тёмная"},
            ],
            "required": True,
            "editable": True,
            "frontend": True,
        },
    ],
}
```

`RESPONSE_METHOD` принимает callable либо строку вида
`"package.module:function"`/`"package.module.function"`. Callable должен
поддерживать keyword-аргументы `data` и `status`.

## Python API

```python
from confetti.api import get, is_enabled, set_value
from confetti.models import SettingScope

# Effective value с учётом override пользователя.
theme = get("ui.theme", user=request.user, default="light")

# User override: scope определяется автоматически по переданному user.
set_value("ui.theme", "dark", user=request.user)

# Global override.
set_value("ui.theme", "light", scope=SettingScope.GLOBAL)

# Удаление user override и возврат к global/default fallback.
set_value("ui.theme", None, user=request.user)

# Проверка bool-флага.
email_enabled = is_enabled(
    "notifications.email.enabled",
    user=request.user,
    default=False,
)
```

`set_value(..., None)` удаляет соответствующую строку `SettingValue` и
возвращает `None`. Для required-настройки reset отклоняется, если после удаления
не останется global/default fallback.

Для `editable=False` запись через публичный API не меняет effective value.

### Bool и `enabled`

У `type="bool"` поле `enabled` является основным переключателем. При создании
и изменении bool-definition поле `default` синхронизируется с `enabled`.
`is_enabled()` использует следующий порядок:

```text
enabled=False → False для всех
enabled=True → user override → global override → enabled
```

`enabled` не управляет видимостью настройки в REST API. За возможность
изменения отвечает `editable`, за включение в публичную frontend-выдачу —
`frontend`.

## REST API

REST-маршруты доступны только с extra `drf`:

```python
from django.urls import include, path

urlpatterns = [
    path(
        "api/confetti/",
        include(("confetti.urls", "confetti"), namespace="confetti"),
    ),
]
```

Если попытаться импортировать `confetti.urls` без DRF, Django выдаст понятную
ошибку с инструкцией установить `django-confetti[drf]`. Основной Python API при
этом продолжает работать без DRF.

Доступные маршруты:

- `GET /api/confetti/settings/` — список definitions;
- `GET /api/confetti/settings/frontend/` — кэшируемый список
  `frontend=True`;
- `GET /api/confetti/settings/<key>/` — definition и effective value;
- `PATCH /api/confetti/settings/<key>/` — записать или удалить override.

PATCH body:

```json
{"value": "dark"}
```

Без `scope` используется user scope. Для global scope:

```json
{"scope": "global", "value": "dark"}
```

Reset выполняется через `{"value": null}`. Неизвестный scope и неверное
типизированное значение возвращают HTTP 400.

| Роль | User scope | Global scope | `editable=False` |
| --- | --- | --- | --- |
| Anonymous | 401 | 403 | Не показывается |
| User | Свой override | 403 | Не показывается |
| Staff | Свой override | Разрешён для `editable=True` | Не показывается |
| Superuser | Свой override | Разрешён | Чтение; effective value защищён от изменения |

List/detail используют стандартные DRF authentication classes проекта.
Авторизованный пользователь получает `user_value`, а `effective` учитывает его
override. Anonymous получает global/default значения. Только superuser видит
definitions с `editable=False`.

## Типы значений

| Тип | Формат |
| --- | --- |
| `bool` | Строго `true`/`false`; числа не принимаются |
| `int` | Целое число или приводимая строка |
| `float` | Число или приводимая строка |
| `str` | Строка; входное значение приводится через `str()` |
| `json` | JSON-сериализуемое значение |
| `choice` | Одно значение или список значений из `choices[*].value` |
| `datetime` | ISO datetime; сохраняется как ISO-строка |
| `duration` | Неотрицательное целое число секунд |

Каждый элемент `choices` должен быть объектом с обязательным ключом `value`.
Для одиночного выбора `default` и override задаются одним значением:

```json
"light"
```

Для множественного выбора используется JSON-массив:

```json
["light", "dark"]
```

Каждый элемент массива должен присутствовать в `choices[*].value`. Одиночный
формат сохранён для обратной совместимости. В Django Admin массив следует
вводить без внешних кавычек: `["light", "dark"]`, а не
`"[\"light\", \"dark\"]"`.

## Поля definition

- `key` — уникальный ключ вида `namespace.setting`;
- `category` — optional-категория;
- `type` — один из типов выше;
- `title`, `description` — отображаемые метаданные;
- `default` — fallback при отсутствии overrides;
- `choices` — допустимые значения для `choice`;
- `required` — запрещает отсутствие effective fallback;
- `enabled` — основной переключатель bool-настройки;
- `editable` — разрешает изменение через Python/REST API;
- `frontend` — включает definition в endpoint `settings/frontend/`.

БД гарантирует одну global-строку на definition и одну user-строку на пару
definition/user. Scope `global` не допускает user, scope `user` требует user.

## Seed и sync

При `AUTO_SEED=True` post-migrate создаёт отсутствующие категории и definitions,
не перезаписывая существующие записи.

```bash
# Создать всё отсутствующее.
python manage.py confetti_seed

# Ограничить seed одной областью.
python manage.py confetti_seed --categories-only
python manage.py confetti_seed --definitions-only

# Обновить title/description/enabled/editable и category.
python manage.py confetti_sync --update

# Дополнительно обновить default/choices/type.
python manage.py confetti_sync --update --update-defaults

# Рассчитать изменения и откатить транзакцию.
python manage.py confetti_sync --dry-run
```

Legacy-форма `-update-defaults` временно поддерживается для совместимости с
версией 0.4.2; новый код должен использовать `--update-defaults`.

## Snapshots

`SettingsSnapshot` хранит definitions, категории и global values. User
overrides в snapshot не входят.

Admin actions позволяют создать snapshot, посмотреть сравнение с текущим
состоянием и восстановить его. Restore:

1. валидирует и нормализует весь payload до записи;
2. создаёт и обновляет definitions/categories/global values;
3. удаляет global value, отсутствующий в snapshot;
4. удаляет definitions, отсутствующие в snapshot;
5. выполняет всё в одной транзакции.

Категории не удаляются, поскольку могут использоваться другими данными. Пустой
snapshot отклоняется, пока явно не передан `allow_empty=True`.

```python
from confetti.services import (
    preview_global_settings_snapshot_restore,
    restore_global_settings_snapshot,
)

preview = preview_global_settings_snapshot_restore(payload)
result = restore_global_settings_snapshot(payload, dry_run=True)
result = restore_global_settings_snapshot(payload)
```

`RestoreResult` содержит счётчики созданных, обновлённых и удалённых definitions,
categories и global values.

## Кэширование

Confetti использует настроенный Django cache. Global/default fallback хранится
в общем ключе, реальный user override — в пользовательском. Signals очищают
кэш при изменении или удалении definitions/values. Frontend-кэш очищается при
изменении global value либо definition; пустой frontend-ответ тоже кэшируется.

## Swagger

При установленном extra `docs` используются аннотации drf-yasg. Без drf-yasg
декораторы становятся no-op; REST API продолжает работать при наличии DRF.

## Обновление с 0.4.2 до 0.5.0

Миграция `0004`:

- заменяет изменяемые JSON defaults на callable;
- нормализует legacy scope/user;
- детерминированно сохраняет effective values при legacy-дубликатах;
- добавляет ограничения уникальности и согласованности scope/user.

Публичные импорты `get`, `set_value`, `is_enabled`, существующие REST URL,
ключи `CONFETTI` и snapshot-формат 0.4.2 сохраняются. Полный список изменений
находится в `CHANGELOG.md`.

## Разработка

`requirements.txt` — UTF-8 снимок dev-окружения. Runtime и optional dependencies
пакета задаются в `pyproject.toml`.

```bash
pytest
python manage.py check
python manage.py makemigrations --check --dry-run
python -m build
```

## Лицензия и репозиторий

MIT. Репозиторий: <https://github.com/sapp1507/django-confetti>
