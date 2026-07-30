import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_0004_preserves_effective_values_while_normalizing_legacy_rows():
    migrate_from = [('confetti', '0003_settingssnapshot_alter_settingdefinition_choices_and_more')]
    migrate_to = [('confetti', '0004_normalize_setting_values_and_constraints')]

    executor = MigrationExecutor(connection)
    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    User = old_apps.get_model('auth', 'User')
    SettingDefinition = old_apps.get_model('confetti', 'SettingDefinition')
    SettingValue = old_apps.get_model('confetti', 'SettingValue')

    user = User.objects.create(username='migration-user')
    definition = SettingDefinition.objects.create(
        key='migration.duplicates',
        type='str',
        title='Migration duplicates',
        default='default',
    )

    # Старый API выбирал первые валидные строки через QuerySet.first().
    SettingValue.objects.create(
        definition=definition,
        scope='global',
        user=None,
        value='primary-global',
    )
    SettingValue.objects.create(
        definition=definition,
        scope='global',
        user=None,
        value='duplicate-global',
    )
    SettingValue.objects.create(
        definition=definition,
        scope='global',
        user=user,
        value='invalid-user-shape',
    )
    SettingValue.objects.create(
        definition=definition,
        scope='user',
        user=user,
        value='primary-user',
    )
    SettingValue.objects.create(
        definition=definition,
        scope='user',
        user=None,
        value='invalid-global-shape',
    )

    orphan_definition = SettingDefinition.objects.create(
        key='migration.normalize-only',
        type='str',
        title='Normalize only',
        default='default',
    )
    SettingValue.objects.create(
        definition=orphan_definition,
        scope='user',
        user=None,
        value='preserved-and-normalized',
    )

    executor = MigrationExecutor(connection)
    executor.migrate(migrate_to)
    new_apps = executor.loader.project_state(migrate_to).apps
    MigratedValue = new_apps.get_model('confetti', 'SettingValue')

    values = list(
        MigratedValue.objects
        .filter(definition_id=definition.pk)
        .order_by('scope')
        .values_list('scope', 'user_id', 'value')
    )
    assert values == [
        ('global', None, 'primary-global'),
        ('user', user.pk, 'primary-user'),
    ]

    normalized = MigratedValue.objects.get(definition_id=orphan_definition.pk)
    assert normalized.scope == 'global'
    assert normalized.user_id is None
    assert normalized.value == 'preserved-and-normalized'
