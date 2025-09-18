import icecream
from django.core.cache import cache

from .models import SettingDefinition, SettingValue, SettingScope
from .validators import validate_value
from .conf import confetti_settings

CACHE_PREFIX = confetti_settings.CACHE_PREFIX

def _ck(def_key, user_id=None):
    return f'{CACHE_PREFIX}:{def_key}:{user_id or "global"}'

def get(def_key: str, user=None, default=None):
    """
    Приоритет: user override -> global -> definition.default -> default (параметр).
    Результат кэшируется.
    """
    uid = getattr(user, 'id', None)
    for key in (_ck(def_key, uid), _ck(def_key, None)):
        cached = cache.get(key)
        if cached is not None and (uid or key.endswith(':global')):
            return cached
    try:
        defn = SettingDefinition.objects.get(key=def_key, enabled=True)
    except SettingDefinition.DoesNotExist:
        return default

    # user override
    if uid:
        sv = SettingValue.objects.filter(definition=defn, scope=SettingScope.USER, user_id=uid).first()

        if sv and sv.value is not None:
            cache.set(_ck(def_key, uid), sv.value)
            return sv.value

    # global
    gv = SettingValue.objects.filter(definition=defn, scope=SettingScope.GLOBAL, user__isnull=True).first()
    if gv and gv.value is not None:
        cache.set(_ck(def_key, None), gv.value)
        return gv.value
    return defn.default if defn.default is not None else default

def set_value(def_key: str, value, user=None, scope=None):
    """
    Устанавливает значение с валидацией по типу.
    scope: None => USER если user передан, иначе GLOBAL.
    """
    defn = SettingDefinition.objects.get(key=def_key)

    value = validate_value(defn, value)
    if scope is None:
        scope = SettingScope.USER if user else SettingScope.GLOBAL

    sv, _ = SettingValue.objects.get_or_create(
        definition=defn, scope=scope, user=user if scope == SettingScope.USER else None
    )
    if not defn.editable:
        value = defn.default
    sv.value = value
    sv.save()
    cache.set(_ck(def_key, sv.user_id if sv.scope == SettingScope.USER else None), value)
    return sv

def is_enabled(flag_key: str, user=None, default=False) -> bool:
    val = get(flag_key, user=user, default=default)
    return bool(val)
