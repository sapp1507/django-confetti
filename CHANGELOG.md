# Changelog

Все значимые изменения проекта документируются в этом файле.

## Unreleased

## 0.5.0 — 2026-07-30

Обратно совместимое обновление после версии `0.4.2`.
До исправления номера этот релиз был ошибочно опубликован как `1.5.0`;
корректная версия — `0.5.0`.

### Added

- Явный extra `drf` и self-contained extra `docs`.
- Validation и dry-run/preview для восстановления snapshots.
- DB-ограничения global/user scope и migration `0004` для legacy-данных.
- Регрессионные тесты Python API, REST, cache, commands, migrations,
  dependencies, configuration и snapshots.

### Changed

- `is_enabled()` использует `enabled` как canonical bool fallback.
- `set_value(..., None)` удаляет override и возвращает `None`.
- `confetti_sync` принимает корректный `--update-defaults`; прежний
  `-update-defaults` сохранён как legacy alias.
- REST list использует стандартные authentication classes проекта.
- Только superuser видит `editable=False`; staff сохраняет global-write для
  `editable=True`.
- `requirements.txt` приведён к UTF-8 и обозначен как dev snapshot.
- Метаданные сборки приведены к современному SPDX-формату.
- Тип `choice` принимает как одиночное значение, так и список значений из
  `choices[*].value`.

### Fixed

- `--categories-only` и `--definitions-only` management-команд.
- Dry-run sync больше не скрывает посторонние `RuntimeError`.
- HTTP 400/401/403 REST responses и обработка неожиданного lookup exception.
- Runtime-import без `icecream`, основной API без DRF и понятная ошибка REST URL
  при отсутствующем extra.
- Mutable defaults у JSONField.
- Дубликаты global values и несогласованные scope/user.
- Приведение int/float/datetime/duration, строгий bool, choice validation и
  преобразование validation errors в HTTP 400.
- Stale `is_enabled` после изменения global value и stale frontend cache.
- Удаление global value при restore, предварительная validation и атомарный
  rollback snapshots.
- Pytest settings, demo choice и кодировка dev requirements.

### Compatibility

- Сохранены публичные импорты `confetti.api.get`, `set_value`, `is_enabled` и
  их параметры.
- Сохранены существующие REST paths/names, ключи `settings.CONFETTI`, модели и
  чтение snapshot payload версии `0.4.2`.
- Migration `0004` применима поверх схемы `0.4.2` и предпочитает прежние
  effective values при нормализации legacy-дубликатов.
