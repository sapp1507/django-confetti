import datetime

import pytest

from confetti.admin import SettingDefinitionAdminForm, SettingValueAdminForm
from confetti.models import SettingDefinition, SettingScope, SettingType
from confetti.validators import validate_value


def definition(setting_type, **kwargs):
    return SettingDefinition(
        key=f'validation.{setting_type}',
        type=setting_type,
        title=f'Validation {setting_type}',
        **kwargs,
    )


@pytest.mark.parametrize(
    ('setting_type', 'value', 'expected'),
    [
        (SettingType.BOOL, True, True),
        (SettingType.INT, '42', 42),
        (SettingType.FLOAT, '2.5', 2.5),
        (SettingType.STR, 42, '42'),
        (SettingType.JSON, {'answer': 42}, {'answer': 42}),
        (SettingType.DATETIME, '2026-07-30T12:30:00', '2026-07-30T12:30:00'),
        (SettingType.DURATION, '60', 60),
    ],
)
def test_validate_value_converts_supported_types(setting_type, value, expected):
    assert validate_value(definition(setting_type), value) == expected


def test_validate_datetime_object_to_iso_string():
    value = datetime.datetime(2026, 7, 30, 12, 30, tzinfo=datetime.timezone.utc)

    assert validate_value(definition(SettingType.DATETIME), value) == '2026-07-30T12:30:00+00:00'


def test_validate_choice_uses_declared_values():
    defn = definition(
        SettingType.CHOICE,
        choices=[{'value': 'light'}, {'value': 'dark'}],
    )

    assert validate_value(defn, 'dark') == 'dark'
    with pytest.raises(ValueError, match='недопустимое'):
        validate_value(defn, 'system')


def test_validate_choice_accepts_list_of_declared_values():
    defn = definition(
        SettingType.CHOICE,
        choices=[{'value': 1}, {'value': 2}, {'value': 3}],
    )

    assert validate_value(defn, [1, 2]) == [1, 2]
    assert validate_value(defn, [2, 3]) == [2, 3]

    with pytest.raises(ValueError, match='недопустимое'):
        validate_value(defn, [2, 4])


@pytest.mark.django_db
def test_setting_definition_admin_form_accepts_choice_list_default():
    form = SettingDefinitionAdminForm(data={
        'key': 'validation.admin-choice-list',
        'category': '',
        'type': SettingType.CHOICE,
        'title': 'Admin choice list',
        'description': '',
        'default': '[2, 3]',
        'choices': '[{"value": 1}, {"value": 2}, {"value": 3}]',
        'required': '',
        'enabled': 'on',
        'editable': 'on',
        'frontend': '',
    })

    assert form.is_valid(), form.errors
    assert form.cleaned_data['default'] == [2, 3]


def test_validate_choice_reports_malformed_choices():
    defn = definition(SettingType.CHOICE, choices=[{'label': 'Missing value'}])

    with pytest.raises(ValueError, match='ключом value'):
        validate_value(defn, 'anything')


@pytest.mark.parametrize(
    ('setting_type', 'value'),
    [
        (SettingType.BOOL, 1),
        (SettingType.INT, True),
        (SettingType.FLOAT, False),
        (SettingType.DATETIME, []),
        (SettingType.DURATION, -1),
    ],
)
def test_validate_value_rejects_invalid_values(setting_type, value):
    with pytest.raises((TypeError, ValueError)):
        validate_value(definition(setting_type), value)


def test_required_value_rejects_none_and_optional_value_allows_it():
    with pytest.raises(ValueError, match='обязательное'):
        validate_value(definition(SettingType.STR, required=True), None)

    assert validate_value(definition(SettingType.STR, required=False), None) is None


@pytest.mark.django_db
def test_admin_form_does_not_persist_null_override():
    defn = SettingDefinition.objects.create(
        key='validation.admin-null',
        type=SettingType.STR,
        title='Admin null',
        default='fallback',
    )
    form = SettingValueAdminForm(data={
        'definition': defn.pk,
        'scope': SettingScope.GLOBAL,
        'user': '',
        'value': '',
    })

    assert not form.is_valid()
    assert 'Удалите запись' in str(form.non_field_errors())
