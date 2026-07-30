import datetime
import json

from .models import SettingDefinition
from .models import SettingType


def validate_value(defn: 'SettingDefinition', value):
    if value is None:
        if defn.required:
            raise ValueError(f'{defn.key}: обязательное значение не может быть null')
        return None

    t = defn.type
    if t == SettingType.BOOL:
        if not isinstance(value, bool):
            raise ValueError('Ожидается bool')
    elif t == SettingType.INT:
        if isinstance(value, bool):
            raise ValueError('Ожидается int, bool не допускается')
        value = int(value)
    elif t == SettingType.FLOAT:
        if isinstance(value, bool):
            raise ValueError('Ожидается float, bool не допускается')
        value = float(value)
    elif t == SettingType.STR:
        value = str(value)
    elif t == SettingType.CHOICE:
        choices = defn.choices or []
        if not isinstance(choices, list) or any(
            not isinstance(choice, dict) or 'value' not in choice
            for choice in choices
        ):
            raise ValueError(
                f'{defn.key}: choices должен быть списком объектов с ключом value'
            )
        allowed = [choice['value'] for choice in choices]
        values = value if isinstance(value, list) else [value]
        if any(item not in allowed for item in values):
            raise ValueError(f'{defn.key}: недопустимое значение для choice')
    elif t == SettingType.JSON:
        json.dumps(value)
    elif t == SettingType.DATETIME:
        if isinstance(value, datetime.datetime):
            parsed = value
        elif isinstance(value, str):
            parsed = datetime.datetime.fromisoformat(value)
        else:
            raise ValueError('Ожидается datetime или строка в ISO-формате')
        value = parsed.isoformat()
    elif t == SettingType.DURATION:
        if isinstance(value, bool):
            raise ValueError('Ожидается длительность в секундах, bool не допускается')
        iv = int(value)
        if iv < 0:
            raise ValueError('Продолжительность меньше 0')
        value = iv
    else:
        raise ValueError(f'Неизвестный тип настройки: {t}')

    return value
