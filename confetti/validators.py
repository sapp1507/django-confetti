import json, datetime

from .models import SettingDefinition
from .models import SettingType


def validate_value(defn: 'SettingDefinition', value):
    t = defn.type
    if t == SettingType.BOOL:
        if not isinstance(value, bool):
            raise ValueError('Ожидается bool')
    elif t == SettingType.INT: value = int(value)
    elif t == SettingType.FLOAT: value = float(value)
    elif t == SettingType.STR: value = str(value)
    elif t == SettingType.CHOICE:
        allowed = [c['value'] for c in (defn.choices or [])]
        for v in value:
            if v not in allowed:
                raise ValueError(f'{defn.key} не допустимое значение для CHOICE')
    elif t == SettingType.JSON:
        json.dumps(value)
    elif t == SettingType.DATETIME:
        datetime.datetime.fromisoformat(value)
    elif t == SettingType.DURATION:
        iv = int(value)
        if iv < 0: raise ValueError('Продолжительность меньше 0')

    return value
