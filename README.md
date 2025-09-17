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

---

## Установка

```bash
pip install django_confetti
```
Добавьте в INSTALLED_APPS:
``` python 
INSTALLED_APPS = [
    # ...
    "confetti",
]
```

## Быстрый старт
Настройка в ``settings.py``
```python
CONFETTI = {
    # Кастомный метод ответа (callable или "pkg.mod:func")
    "RESPONSE_METHOD": "myproject.api.responses:api_response", # default rest_framework.response.Response or django.http.JsonResponse

    # Автосидирование дефолтных настроек
    "AUTO_SEED": True,

    "SEED_CATEGORIES": [
        {"code": "scheduler", "title": "Планировщик"},
        {"code": "notifications", "title": "Уведомления"},
    ],

    "SEED_DEFINITIONS": [
        {
            "key": "feature.scheduler.enable_jobs",
            "type": "bool",
            "category": "scheduler",
            "title": "Включить планировщик",
            "default": True,
        },
        {
            "key": "job.cleanup.schedule",
            "type": "cron",
            "category": "scheduler",
            "title": "Cron очистки",
            "default": "0 3 * * *",
        },
        {
            "key": "notifications.email.enabled",
            "type": "bool",
            "category": "notifications",
            "title": "Почтовые уведомления",
            "default": True,
        },
    ],
}
```

## Исользование API
```python
from confetti.api import get, is_enabled, set_value
from confetti.conf import confetti_settings

# Получение значения
jobs_enabled = is_enabled("feature.scheduler.enable_jobs")  # True / False

# Учитывает пользовательские override
theme = get("ui.theme", user=request.user, default="light")

# Установка значения
set_value("ui.theme", "dark", user=request.user)

# Универсальный ответ (DRF Response или JsonResponse)
return confetti_settings.RESPONSE_METHOD(data={"status": "ok"}, status=200)

```

## REST API
```python
# project/urls.py
urlpatterns = [
    # ...
    path("api/confetti/", include("confetti.urls", namespace="confetti")),
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

``scope="user"`` или без ``scope``: создаёт/обновляет пользовательское значение (требует авторизацию).

``scope="global"``: меняет глобальное значение (требует ``is_staff/is_superuser``).

Удалять нельзя. Чтобы вернуть ``default``, можно передать ``{"value": null}``.

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
