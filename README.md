# Django Confetti 🎉

**Django Confetti** — это модуль управления настройками для Django, вдохновлённый архитектурой `REST_FRAMEWORK` и подходами feature-flag систем.  
Он позволяет централизованно описывать и хранить глобальные и пользовательские настройки приложения, группировать их по категориям, автоматически сидировать дефолты и использовать через удобный API.

---

## Возможности

- 🔑 **Централизованные определения настроек** (`SettingDefinition`) с категориями, типами и значениями по умолчанию.  
- 👤 **Поддержка пользовательских override** (`SettingValue`): значение можно задать глобально или для конкретного пользователя.  
- ⚡ **Кэширование** и автоматическая инвалидация через Django signals.  
- 🛠 **Автосидирование**: дефолтные категории/настройки создаются при `migrate` (без перезаписи существующих).  
- 🔄 **Команды управления**:  
  - `confetti_seed` — создать недостающие настройки из `settings.CONFETTI`.  
  - `confetti_sync` — синхронизировать с флагами обновления полей.  
- 📦 **API & Views**: готовые эндпоинты для получения/обновления настроек (DRF).  
- 📜 **Swagger** (опционально, через `drf-yasg`): документация к API включается автоматически.  
- 🧩 **Конфиг через Django settings**: как в DRF (`CONFETTI = {...}`), с поддержкой `dotted path` для функций.  
- 🚀 **Fallback без DRF**: работает даже если в проекте нет DRF или `drf-yasg`.
- 📸 **Snapshots глобальных настроек**: можно сохранить снимок текущего состояния и восстановить его позже.
- ♻️ **Восстановление с синхронизацией**: при restore создаются недостающие настройки, обновляются существующие и удаляются настройки, которых нет в snapshot.

---

## Установка

```bash
pip install django_confetti
```
Добавьте в INSTALLED_APPS:
``` python 
INSTALLED_APPS = [
    # ...
    'confetti',
]
```

## Быстрый старт
Настройка в ``settings.py``
```python
CONFETTI = {
    'FRONTEND_CACHE_TIMEOUT': 300, # секунды
    # Кастомный метод ответа (callable или 'pkg.mod:func')
    'RESPONSE_METHOD': 'myproject.api.responses:api_response', # default rest_framework.response.Response or django.http.JsonResponse

    # Автосидирование дефолтных настроек
    'AUTO_SEED': True,

    # Категории
    'SEED_CATEGORIES': [
        {'code': 'scheduler', 'title': 'Планировщик'},
        {'code': 'notifications', 'title': 'Уведомления'},
    ],
    # Настройки
    'SEED_DEFINITIONS': [
        { 
            'key': 'str',                               # required
            'category': ForeignKey(SettingCategory),    # null=True
            'type': SettingType.choices,                # required
            'title': ChaField,                          # required
            'description': TextField,                   # blank=True
            'default': JSONFiled,                       # null=True
            'choices': JSONField,                       # null=True
            'required': False,                          # default
            'enabled': True,                            # default
            'editable': True,                           # default
            'frontend': False,                          # default 
        },
        {
          # Минимальный рекомендуемый набор параметров для создания
            'key': 'notifications.email.enabled',
            'type': 'bool',
            'category': 'notifications',
            'title': 'Почтовые уведомления',
            'default': True,
        },
    ],
}
```

## Исользование API
```python
from confetti.api import get, is_enabled, set_value
from confetti.conf import confetti_settings

# Получение значения Вкл\выкл настройки
jobs_enabled = is_enabled('feature.scheduler.enable_jobs')  # True / False

# Учитывает пользовательские override
theme = get('ui.theme', user=request.user, default='light')

# Установка значения
set_value('ui.theme', 'dark', user=request.user)

# Универсальный ответ (DRF Response или JsonResponse)
return confetti_settings.RESPONSE_METHOD(data={'status': 'ok'}, status=200)

```

## REST API
```python
# project/urls.py
urlpatterns = [
    # ...
    path('api/confetti/', include('confetti.urls', namespace='confetti')),
]
```

## Доступные эндпоинты
Доступные эндпоинты

* ``GET /api/confetti/settings/``
Список всех настроек.

  * Аноним: только глобальные и default.
  * Авторизованный: добавляется ``user_value`` и ``effective`` учитывает override.

* ``GET /api/confetti/settings/<key>/``
Получить одну настройку.

    * ``PATCH /api/confetti/settings/<key>/``
Обновить настройку.

``scope='user'`` или без ``scope``: создаёт/обновляет пользовательское значение (требует авторизацию).

``scope='global'``: меняет глобальное значение (требует ``is_staff/is_superuser``).

Удалять нельзя. Чтобы вернуть ``default``, можно передать ``{'value': null}``.


## Snapshot в админке

В `Django Admin` доступны 2 action:

- На странице **SettingDefinition**: `Сохранить snapshot (снимок) всех глобальных настроек` — сохраняет полный снимок реестра настроек и глобальных значений в `SettingsSnapshot`.
- На странице **SettingsSnapshot**: `Восстановить настройки из snapshot (лишние настройки будут удалены)` — применяет выбранный snapshot к текущему состоянию.

Алгоритм восстановления:

1. Система берет `payload` из snapshot.
2. Создает отсутствующие категории и настройки.
3. Обновляет поля существующих настроек и их глобальные значения.
4. Удаляет текущие настройки, которых нет в snapshot.

В карточке snapshot есть блок сравнения с текущим состоянием (`comparison_report`), чтобы перед восстановлением увидеть отличия: что изменилось, чего не хватает и что будет удалено.

## Управление через команды
```bash
# Создать недостающие (не трогает существующие)
python manage.py confetti_seed

# Синхронизировать (обновляет безопасные поля)
python manage.py confetti_sync --update

# Синхронизировать + обновить default/choices/type
python manage.py confetti_sync --update --update-defaults

# Только посмотреть, что изменится
python manage.py confetti_sync --dry-run

```

## Swagger (Опционально)
Если в проекте есть ``drf-yasg``, Confetti автоматически добавляет аннотации.
Если нет — проект работает без него (декораторы превращаются в no-op).

Для установки с поддержкой документации:
```bash
pip install django_confetti[docs]
```

## Поля модели
* key
  
  Уникальный строковый идентификатор настройки.
  Используется в коде через get("celery.send_email").
  Хорошая практика — делать "namespace.key" (например, celery.send_email, ui.theme).


* `type` (``models.SettingType``)
  
  Тип данных, который допускается для этой настройки. Поддерживаются:
  * `bool` — булевы значения (вкл/выкл)
  * `int`, float — числа
  * `str` — строка
  * `choice` — список объектов доступный к выбору. У объекта ключ `value` обязателен Пример: [{'title': 'Роль', 'value': 1}]
  * `json` — произвольный JSON-объект
  * `datetime`  — дата и время
  * `duration` - целое положительное число в секундах


* `category`

  Ссылка на категорию (например, scheduler, ui, notifications).
  Нужна для группировки настроек в админке, в API и для удобного поиска.

* `title`

  Человекочитаемое название настройки (для админки/документации).

* `default`

  Значение по умолчанию (используется, если нет ни глобального, ни пользовательского override).
  Тип должен совпадать с `type`.

* `description`

  Текстовое описание, зачем нужна настройка.
  Показывается в админке и может попадать в документацию API.

* `required`

  Флаг «обязательная настройка».

  * Если True → значение должно быть задано (нельзя оставить null/None).

  * Если False → допускается null (или fallback к default).

* `enabled`

  Флаг активности настройки.

  * Если False → настройка считается выключенной (не доступна через API / может не отображаться в интерфейсе).

  Полезно для временного отключения без удаления.

* `editable`

  Флаг «можно ли менять через админку/API».

  * False → только чтение (например, «системная» настройка, задаётся через миграцию/сидер).

  Полезно для защищённых фич или «констант».

* `frontend`

  Настройка указывает что она используется для клиента. (отдельная api для запроса фронт настроек)

## Архитектура
    
* SettingCategory — категории для группировки.

* SettingDefinition — описание настройки: ключ, тип (bool, int, str, json, choice, cron, rrule, …), дефолт.

* SettingValue — конкретное значение: глобальное или для пользователя.

* Кэширование: значения хранятся в Django cache (confetti:v1:{key}:{user_id|global}), инвалидируются сигналами.

* Seed/sync: автоматическое создание из settings.CONFETTI.

## Требования

* Python 3.10+
* Django 3.2+
* (опционально) Django REST Framework
* (опционально) drf-yasg

## Ссылка на github
* https://github.com/sapp1507/django-confetti
