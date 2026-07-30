import django
from django.db import migrations, models


def normalize_setting_values(apps, schema_editor):
    """Подготавливает данные 0.4.2 к строгим ограничениям scope/user.

    При наличии нескольких строк сохраняется самая ранняя валидная строка —
    именно её возвращал прежний QuerySet.first(). Если валидной строки нет,
    сохраняется самая ранняя и её scope нормализуется по наличию user.
    """
    SettingValue = apps.get_model('confetti', 'SettingValue')

    kept_by_target = {}
    delete_ids = []
    normalize_ids = []

    rows = SettingValue.objects.order_by('pk').values(
        'pk',
        'definition_id',
        'scope',
        'user_id',
    )
    for row in rows:
        desired_scope = 'user' if row['user_id'] is not None else 'global'
        target = (row['definition_id'], row['user_id'])
        is_valid = row['scope'] == desired_scope
        kept = kept_by_target.get(target)

        if kept is None:
            kept_by_target[target] = {**row, 'is_valid': is_valid}
            continue

        if is_valid and not kept['is_valid']:
            delete_ids.append(kept['pk'])
            kept_by_target[target] = {**row, 'is_valid': True}
        else:
            delete_ids.append(row['pk'])

    if delete_ids:
        SettingValue.objects.filter(pk__in=delete_ids).delete()

    for kept in kept_by_target.values():
        desired_scope = 'user' if kept['user_id'] is not None else 'global'
        if kept['scope'] != desired_scope:
            normalize_ids.append((kept['pk'], desired_scope))

    for pk, desired_scope in normalize_ids:
        SettingValue.objects.filter(pk=pk).update(scope=desired_scope)


class Migration(migrations.Migration):

    dependencies = [
        ('confetti', '0003_settingssnapshot_alter_settingdefinition_choices_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_setting_values, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name='settingvalue',
            name='unique_setting_value',
        ),
        migrations.AddConstraint(
            model_name='settingvalue',
            constraint=models.CheckConstraint(
                **{
                    'condition' if django.VERSION >= (5, 1) else 'check': (
                        models.Q(scope='global', user__isnull=True)
                        | models.Q(scope='user', user__isnull=False)
                    ),
                    'name': 'valid_setting_scope_user',
                }
            ),
        ),
        migrations.AddConstraint(
            model_name='settingvalue',
            constraint=models.UniqueConstraint(
                condition=models.Q(scope='global', user__isnull=True),
                fields=('definition',),
                name='unique_global_setting_value',
            ),
        ),
        migrations.AddConstraint(
            model_name='settingvalue',
            constraint=models.UniqueConstraint(
                condition=models.Q(scope='user', user__isnull=False),
                fields=('definition', 'user'),
                name='unique_user_setting_value',
            ),
        ),
        migrations.AlterField(
            model_name='settingdefinition',
            name='choices',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Список объектов, у объекта ключ value обязателен, этот ключ храниться в default в виде списка',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='settingdefinition',
            name='default',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
