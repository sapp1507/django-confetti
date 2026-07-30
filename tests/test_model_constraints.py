import pytest
from django.db import IntegrityError, transaction

from confetti.models import (
    SettingDefinition,
    SettingScope,
    SettingType,
    SettingValue,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def definition():
    return SettingDefinition.objects.create(
        key='constraints.example',
        type=SettingType.STR,
        title='Constraints example',
        default='default',
    )


def test_json_defaults_are_not_shared_between_definitions():
    first = SettingDefinition(key='constraints.first', type=SettingType.JSON, title='First')
    second = SettingDefinition(key='constraints.second', type=SettingType.JSON, title='Second')

    first.default.append('first')
    first.choices.append({'value': 'first'})

    assert second.default == []
    assert second.choices == []


def test_only_one_global_value_is_allowed(definition):
    SettingValue.objects.create(
        definition=definition,
        scope=SettingScope.GLOBAL,
        user=None,
        value='first',
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        SettingValue.objects.create(
            definition=definition,
            scope=SettingScope.GLOBAL,
            user=None,
            value='second',
        )


def test_only_one_value_per_user_is_allowed(definition, user):
    SettingValue.objects.create(
        definition=definition,
        scope=SettingScope.USER,
        user=user,
        value='first',
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        SettingValue.objects.create(
            definition=definition,
            scope=SettingScope.USER,
            user=user,
            value='second',
        )


@pytest.mark.parametrize(
    ('scope', 'with_user'),
    [
        (SettingScope.GLOBAL, True),
        (SettingScope.USER, False),
    ],
)
def test_scope_and_user_must_match(definition, user, scope, with_user):
    with pytest.raises(IntegrityError), transaction.atomic():
        SettingValue.objects.create(
            definition=definition,
            scope=scope,
            user=user if with_user else None,
            value='invalid',
        )
