# Контекст проекта django-confetti

Документ составлен по состоянию ветки `dev`, commit `b8108b9`, 30 июля 2026 года.
Его назначение — быстро восстановить технический контекст перед следующей сессией
разработки. Основной пользовательский документ проекта — `README.md`; здесь
зафиксированы также фактическая архитектура, команды проверки и известные
расхождения текущего кода с документацией.

## Что это за проект

`django-confetti` — устанавливаемое Django-приложение для динамических настроек
и feature flags. Определения настроек и их значения хранятся в БД, при этом
значение может быть общим для всего приложения или переопределённым для
конкретного пользователя.

Основной пакет — `confetti/`. Каталог `core/` — минимальный Django-проект для
локального запуска и ручной проверки, а не основная часть библиотеки. Метаданные
пакета находятся в `pyproject.toml`: версия `1.5.0`, Python `>=3.10`, Django
`>=3.2`, лицензия MIT. DRF объявлен extra `drf`; extra `docs` включает DRF и
drf-yasg. Основной Python API не требует этих optional dependencies.

## Модель данных

- `SettingCategory` — категория с уникальным slug-кодом и названием.
- `SettingDefinition` — реестр настроек: уникальный `key`, категория, тип,
  описание, default, choices и флаги `required`, `enabled`, `editable`,
  `frontend`.
- `SettingValue` — глобальное либо пользовательское значение. Scope — `global`
  или `user`; пользователь у глобального значения должен быть `NULL`.
- `SettingsSnapshot` — JSON-снимок всех определений и их глобальных значений.

Типы определений: `bool`, `int`, `float`, `str`, `json`, `choice`, `datetime`,
`duration`. Проверка и частичное приведение типов реализованы в
`confetti/validators.py`.

## Как вычисляется значение

Публичный Python API находится в `confetti/api.py`:

- `get(key, user=None, default=None)` использует приоритет user override →
  global value → definition default → аргумент `default`;
- `set_value(...)` проверяет тип и записывает user/global override;
- `is_enabled(...)` сначала учитывает `SettingDefinition.enabled`, затем
  вычисляет значение с тем же приоритетом.

Значения кэшируются стандартным Django cache с префиксом `confetti:v1`.
Signals из `confetti/signals.py` инвалидируют кэш после изменения определений и
значений. Frontend-выдача имеет отдельный ключ и TTL (по умолчанию 300 секунд).

Для bool-определения `enabled` является основным переключателем, а не флагом
видимости настройки. При создании его `default` намеренно становится равен
`enabled`; при последующем изменении `enabled` default снова синхронизируется с
ним. `editable` отдельно определяет возможность изменения настройки.

## Конфигурация и сидирование

Настройки читаются из `settings.CONFETTI` через ленивую обёртку
`confetti/conf.py`. Поддерживается импорт callable по dotted path или записи
`package.module:function`. Основные ключи:

- `CACHE_PREFIX`, `FRONTEND_CACHE_PREFIX`, `FRONTEND_CACHE_TIMEOUT`;
- `RESPONSE_METHOD`;
- `AUTO_SEED`;
- `SEED_CATEGORIES`, `SEED_DEFINITIONS`.

При `post_migrate` и включённом `AUTO_SEED` создаются отсутствующие записи.
Исключения автосидирования сейчас намеренно подавляются. Ручные команды:

```bash
python manage.py confetti_seed
python manage.py confetti_sync --update
python manage.py confetti_sync --dry-run
```

## HTTP API и admin

При подключении `confetti.urls` доступны:

- `GET settings/` — список определений;
- `GET settings/frontend/` — кэшируемые frontend-настройки;
- `GET settings/<key>/` — одна настройка;
- `PATCH settings/<key>/` — user override либо global override для staff/admin.

Обычным пользователям API показывает только `editable=True`; superuser может
читать также защищённые определения. Сериализованный ответ содержит default,
global/user value и effective value. Swagger-аннотации через drf-yasg
опциональны и заменяются no-op совместимым слоем при его отсутствии.

Django Admin позволяет редактировать категории, определения и значения,
очищать кэш, создавать снимок реестра, сравнивать снимок с текущим состоянием и
восстанавливать его. Restore транзакционный: создаёт/обновляет записи из снимка
и удаляет определения, которых в снимке нет.

## Структура репозитория

- `confetti/models.py` — модели и enum типов/scope;
- `confetti/api.py` — Python API и кэш;
- `confetti/views.py`, `serializers.py`, `urls.py` — DRF API;
- `confetti/seed.py` — seed/sync;
- `confetti/services.py` — создание и восстановление snapshots;
- `confetti/admin.py` — формы, списки, actions и сравнение snapshots;
- `confetti/signals.py` — инвалидация кэша;
- `confetti/conf.py`, `defaults.py`, `responses.py` — интеграционные настройки;
- `confetti/openapi.py`, `swagger_compat.py` — схема API;
- `confetti/migrations/` — четыре миграции; `0004` нормализует legacy values,
  исправляет JSON defaults и добавляет ограничения scope/user;
- `tests/` — pytest/pytest-django тесты Python API, REST, admin, seed, cache,
  snapshots и swagger compatibility;
- `core/` и `manage.py` — локальный Django harness;
- `django-confetti.zip` — legacy snapshot сентября 2025 года с pycache; архив
  сохранён для истории и не участвует в setuptools-сборке;
- `requirements.txt` — UTF-8 снимок локального dev-окружения, тогда как
  канонические зависимости пакета описаны в `pyproject.toml`;

## Текущее состояние проверок

Использованные команды:

```bash
pytest -q
python manage.py check
python manage.py makemigrations --check --dry-run
```

Исходный результат на момент составления документа:

- исходный baseline: 22 passed, 1 failed;
- падение `tests/test_api_core.py::test_edit_not_editable` было вызвано
  устаревшим ожиданием теста: для bool значение `enabled=True` намеренно имеет
  приоритет над конфликтующим `default=False`;
- pytest предупреждает, что в `pytest.ini` написано `DJANGO_SETTING_MODULE`
  вместо `DJANGO_SETTINGS_MODULE`;
- Django check выдаёт два `fields.E010`: поля `default` и `choices` используют
  изменяемый `default=[]` вместо callable;
- незаписанных миграций нет.

После выполнения пунктов 1–12 устаревший тест исправлен,
`is_enabled()` явно использует `enabled` как fallback для bool, scope-флаги
команд работают, а обе формы `--update-defaults`/`-update-defaults`
поддерживаются для совместимости. REST корректно возвращает 400/401/403 и не
скрывает неожиданные ошибки lookup. Runtime больше не зависит от `icecream`,
а отсутствие DRF поддерживается для основного Python API. JSON defaults и
ограничения scope/user исправлены совместимой migration `0004`. `value=null`
удаляет override, типы приводятся единообразно, а ошибки REST возвращают 400.
Global fallback `is_enabled` и frontend responses корректно инвалидируются.
Snapshot restore валидируется до записи, удаляет отсутствующий global override
и поддерживает preview/dry-run с атомарным rollback. REST list использует
стандартную DRF authentication, а README и CHANGELOG соответствуют текущим
контрактам. Choice поддерживает одиночное значение и список разрешённых
значений. Текущий результат: 82 passed; Django system check чистый, pytest
выполняется без warnings. Wheel/sdist проходят twine и install smoke matrix на
Django 3.2.25–6.0.7, DRF 3.14.0–3.17.1 и drf-yasg 1.21.5–1.21.15.

## Оставшаяся работа

Исходные известные дефекты и план 1–12 выполнены. Версия релиза установлена в
`1.5.0`, изменения перенесены в версионный раздел CHANGELOG, финальные wheel и
sdist собраны и прошли `twine check`. Перед публикацией остаются commit/tag и
сам publish. Python 3.10 отсутствовал в среде, поэтому отдельный smoke нижней
границы Python ещё желателен в CI.

## Практический старт следующей сессии

1. Проверить `git status --short` и не трогать несвязанные пользовательские
   файлы. На момент анализа в рабочем дереве уже был untracked `un.txt`.
2. Активировать существующее `.venv`, если окружение не активировано.
3. Запустить `pytest -q` и `python manage.py check`.
4. При изменении моделей обязательно выполнить
   `python manage.py makemigrations --check --dry-run` и затем полный тестовый
   набор.
5. Для изменения контракта bool/enabled, snapshot restore или cache
   invalidation сначала добавить регрессионный тест: это ключевые поведенческие
   контракты библиотеки.
