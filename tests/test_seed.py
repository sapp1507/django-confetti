import pytest
from django.apps import apps
from django.core.management import call_command
from django.db.models.signals import post_migrate

from confetti.models import SettingCategory, SettingDefinition

pytestmark = pytest.mark.django_db


def set_confetti_settings(settings, *, categories=None, definitions=None):
    settings.CONFETTI = {
        'AUTO_SEED': False,
        'SEED_CATEGORIES': categories or [],
        'SEED_DEFINITIONS': definitions or [],
    }

    from confetti.conf import confetti_settings
    confetti_settings.reload()


def test_auto_seed_post_migrate_creates_missing(settings):
    app_config = apps.get_app_config("confetti")
    post_migrate.send(sender=app_config.__class__, app_config=app_config, verbosity=0, interactive=False, using='default')
    assert SettingCategory.objects.filter(code='scheduler').exists()
    assert SettingDefinition.objects.filter(key='feature.jobs').exists()


def test_confetti_seed_command_idempotent(settings):
    # первый прогон
    call_command('confetti_seed', verbosity=0)
    c1 = SettingCategory.objects.count()
    d1 = SettingDefinition.objects.count()
    # второй прогон — ничего не меняется
    call_command('confetti_seed', verbosity=0)
    assert SettingCategory.objects.count() == c1
    assert SettingDefinition.objects.count() == d1


def test_confetti_seed_categories_only(settings):
    set_confetti_settings(
        settings,
        categories=[{'code': 'command-category', 'title': 'Command category'}],
        definitions=[{
            'key': 'command.category-definition',
            'type': 'str',
            'category': 'command-category',
            'title': 'Must not be created',
            'default': 'value',
        }],
    )

    call_command('confetti_seed', '--categories-only', verbosity=0)

    assert SettingCategory.objects.filter(code='command-category').exists()
    assert not SettingDefinition.objects.filter(key='command.category-definition').exists()


def test_confetti_seed_definitions_only(settings):
    set_confetti_settings(
        settings,
        categories=[{'code': 'unused-category', 'title': 'Unused category'}],
        definitions=[{
            'key': 'command.definition-only',
            'type': 'str',
            'category': 'required-category',
            'title': 'Definition only',
            'default': 'value',
        }],
    )

    call_command('confetti_seed', '--definitions-only', verbosity=0)

    definition = SettingDefinition.objects.get(key='command.definition-only')
    assert definition.category.code == 'required-category'
    assert not SettingCategory.objects.filter(code='unused-category').exists()


def test_confetti_sync_update_and_update_defaults_aliases(settings):
    categories = [{'code': 'sync-category', 'title': 'Sync category'}]
    definition = {
        'key': 'command.sync',
        'type': 'str',
        'category': 'sync-category',
        'title': 'Before',
        'description': 'Before description',
        'default': 'v1',
    }
    set_confetti_settings(settings, categories=categories, definitions=[definition])
    call_command('confetti_seed', verbosity=0)

    definition = {**definition, 'title': 'After', 'default': 'v2'}
    set_confetti_settings(settings, categories=categories, definitions=[definition])
    call_command('confetti_sync', '--update', verbosity=0)

    stored = SettingDefinition.objects.get(key='command.sync')
    assert stored.title == 'After'
    assert stored.default == 'v1'

    call_command('confetti_sync', '--update', '--update-defaults', verbosity=0)
    stored.refresh_from_db()
    assert stored.default == 'v2'

    definition = {**definition, 'default': 'v3'}
    set_confetti_settings(settings, categories=categories, definitions=[definition])
    call_command('confetti_sync', '--update', '-update-defaults', verbosity=0)
    stored.refresh_from_db()
    assert stored.default == 'v3'


def test_confetti_sync_dry_run_rolls_back(settings):
    set_confetti_settings(
        settings,
        categories=[{'code': 'dry-run', 'title': 'Dry run'}],
        definitions=[{
            'key': 'command.dry-run',
            'type': 'str',
            'category': 'dry-run',
            'title': 'Dry run',
            'default': 'value',
        }],
    )

    call_command('confetti_sync', '--dry-run', verbosity=0)

    assert not SettingCategory.objects.filter(code='dry-run').exists()
    assert not SettingDefinition.objects.filter(key='command.dry-run').exists()


def test_confetti_sync_dry_run_does_not_hide_runtime_error(monkeypatch):
    def fail_seed(**kwargs):
        raise RuntimeError('real sync failure')

    monkeypatch.setattr(
        'confetti.management.commands.confetti_sync.seed_from_settings',
        fail_seed,
    )

    with pytest.raises(RuntimeError, match='real sync failure'):
        call_command('confetti_sync', '--dry-run', verbosity=0)
