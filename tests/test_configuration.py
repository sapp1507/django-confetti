from pathlib import Path

from confetti.models import SettingDefinition, SettingType
from confetti.validators import validate_value
from core import settings as demo_settings


def test_demo_confetti_definitions_use_supported_types_and_values():
    supported_types = {value for value, _label in SettingType.choices}

    for item in demo_settings.CONFETTI['SEED_DEFINITIONS']:
        assert item['type'] in supported_types
        definition = SettingDefinition(
            key=item['key'],
            type=item['type'],
            title=item['title'],
            choices=item.get('choices'),
            required=item.get('required', False),
            enabled=item.get('enabled', True),
        )
        assert validate_value(definition, item.get('default')) == item.get('default')


def test_requirements_snapshot_is_utf8_and_has_no_runtime_debug_dependency():
    requirements_path = Path(__file__).resolve().parents[1] / 'requirements.txt'
    content = requirements_path.read_text(encoding='utf-8')

    assert 'Зависимости пакета: pyproject.toml.' in content
    assert 'icecream' not in content.lower()
