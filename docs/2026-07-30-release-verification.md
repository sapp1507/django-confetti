# Финальная проверка django-confetti

Дата: 2026-07-30.

Ветка: `fix/compatibility-bugfixes`.

Основная матрица совместимости выполнялась для unreleased-состояния поверх
версии `0.4.2`. После выбора версии релиза проверки проекта и сборка финальных
артефактов `1.5.0` повторены. Артефакты создавались только во временном каталоге
`/tmp` и не добавлялись в рабочее дерево.

## Рабочее дерево

Команды:

```bash
pytest -q
python manage.py check
python manage.py makemigrations --check --dry-run
```

Результат:

- 82 теста прошли без warnings;
- Django system check: `0 issues`;
- migration check: `No changes detected`;
- `git diff --check` не находит whitespace errors.

## Сборка

Из временной копии выполнено:

```bash
python -m build
python -m twine check <wheel> <sdist>
```

Успешно созданы и проверены:

- `django_confetti-1.5.0-py3-none-any.whl`;
- `django_confetti-1.5.0.tar.gz`.

Sdist содержит README, CHANGELOG, LICENSE, package modules, management commands
и миграции `0001`–`0004`. Оба финальных артефакта прошли `twine check`; metadata
содержит версию `1.5.0` и README в качестве Markdown-описания пакета.

## Матрица установки

| Вариант | Python | Django | DRF | drf-yasg | Результат |
| --- | --- | --- | --- | --- | --- |
| Core-only wheel | 3.12.3 | 6.0.7 | Не установлен | Не установлен | migrate/API/JsonResponse OK |
| `[drf]` wheel | 3.12.3 | 6.0.7 | 3.17.1 | Не установлен | check/URL/Response OK |
| `[docs]` wheel | 3.12.3 | 6.0.7 | 3.17.1 | 1.21.15 | URL/Swagger imports OK |
| Minimum Django core | 3.11 | 3.2.25 | Не установлен | Не установлен | migrate/check/API OK |
| Minimum extras | 3.11 | 3.2.25 | 3.14.0 | 1.21.5 | migrate/check/URL/Swagger OK |
| Core-only sdist | 3.12.3 | 6.0.7 | Не установлен | Не установлен | build/install/migrate OK |

Проверка включала создание БД с нуля и применение migration `0004` на Django
3.2.25 и 6.0.7. Отдельный тест проекта проверяет обновление `0003 → 0004` с
legacy-дубликатами и несогласованными scope/user.

## Ограничения проверки

Python 3.10 в среде отсутствует. Metadata `requires-python = ">=3.10"`
проверена при сборке, но runtime smoke на Python 3.10 следует добавить в CI.
Нижняя граница Django 3.2.25 успешно проверена на доступном Python 3.11.

## Перед публикацией

Версия релиза установлена: `1.5.0`. Tests/check/build/twine и metadata
финальных артефактов проверены. Остаётся создать commit/tag и выполнить publish
отдельным явным действием.
