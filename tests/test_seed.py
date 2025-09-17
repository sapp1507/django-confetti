import pytest
from django.core.management import call_command
from confetti.models import SettingCategory, SettingDefinition

pytestmark = pytest.mark.django_db


def test_auto_seed_post_migrate_creates_missing(settings):
    # запустим миграции (post_migrate триггерит сидер)
    call_command("migrate", run_syncdb=True, verbosity=0)
    assert SettingCategory.objects.filter(code="scheduler").exists()
    assert SettingDefinition.objects.filter(key="feature.jobs").exists()


def test_confetti_seed_command_idempotent(settings):
    # первый прогон
    call_command("confetti_seed", verbosity=0)
    c1 = SettingCategory.objects.count()
    d1 = SettingDefinition.objects.count()
    # второй прогон — ничего не меняется
    call_command("confetti_seed", verbosity=0)
    assert SettingCategory.objects.count() == c1
    assert SettingDefinition.objects.count() == d1
