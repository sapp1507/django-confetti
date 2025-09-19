from __future__ import annotations
from typing import Literal, Optional
from django.db import transaction

from .conf import confetti_settings
from .models import SettingCategory, SettingDefinition


SafeUpdateFields = ('title', 'description', 'enabled', 'editable')
DefaultUpdateFields = ('default', 'choices', 'type')


@transaction.atomic
def seed_from_settings(
        *,
        update: bool = False,
        update_defaults: bool = False,
        only: Optional[Literal['categories', 'definitions']] = None,
        stdout=None,
        stderr=None,
) -> dict:
    """
    Создает недостающие сущности из settings.CONFETI.
    Если update-True - безопасно обновлять существующие (title, description, enabled, editable).
    Если update_defaults=True - дополнительно обновлять defaults, choices и type
    only: 'categories' | 'definitions' - ограничить область.
    Возвращает счетчики.
    """
    stats = {'created_categories': 0, 'updated_categories': 0,
             'created_definitions': 0, 'updated_definitions': 0}

    def echo(msg: str, stream='out'):
        io = stdout if stream == 'out' else (stderr or stdout)
        if io: io.write(msg)

    if only in (None, 'categories'):
        for c in confetti_settings.SEED_CATEGORIES or []:
            code = (c.get('code') or '').strip()
            if not code:
                continue

            defaults = {'title': c.get('title') or code.title()}
            obj, created = SettingCategory.objects.get_or_create(code=code, defaults=defaults)
            if created:
                stats['created_categories'] += 1
                echo(f'[confetti] created category: {code}')
            elif update:
                changed = False
                if obj.title != defaults['title']:
                    obj.title = defaults['title']
                    changed = True
                if changed:
                    obj.save(update_fields=['title'])
                    stats['updated_categories'] += 1
                    echo(f'[confetti] updated category: {code}')

    if only in (None, 'definition'):
        for d in confetti_settings.SEED_DEFINITIONS or []:
            key = (d.get('key') or '').strip()
            if not key: continue

            cat_code = (d.get('category') or '').strip()
            category = None
            if cat_code:
                category, _ = SettingCategory.objects.get_or_create(
                    code=cat_code,
                    defaults={'title': cat_code.title()}
                )
            defaults = {
                'category': category,
                'type': d.get('type') or 'json',
                'title': d.get('title') or key,
                'description': d.get('description') or '',
                'default': d.get('default'),
                'choices': d.get('choices'),
                'required': bool(d.get('required', False)),
                'enabled': bool(d.get('required', True)),
                'editable': bool(d.get('editable', True)),
                'frontend': bool(d.get('frontend', False)),
            }

            obj, created = SettingDefinition.objects.get_or_create(key=key, defaults=defaults)

            if created:
                stats['created_definitions'] += 1
                echo(f'[confetti] created definition: {key}')
            elif update:
                changed_fields = []
                for f in SafeUpdateFields:
                    val = defaults[f]
                    if getattr(obj, f) != val:
                        setattr(obj, f, val)
                        changed_fields.append(f)
                if update_defaults:
                    for f in DefaultUpdateFields:
                        val = defaults[f]
                        if getattr(obj, f) != val:
                            setattr(obj, f, val)
                            changed_fields.append(f)

                if category and obj.category_id != category.id:
                    obj.category = category
                    changed_fields.append('category')

                if changed_fields:
                    obj.save(update_fields=list(set(changed_fields)))
                    stats['updated_definitions'] += 1
                    echo(f'[confetti] updated definition: {key} (fields: {", ".join(sorted(set(changed_fields)))}')

    return stats
