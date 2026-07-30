from django.core.cache import cache

from .models import SettingDefinition, SettingScope, SettingType, SettingValue
from .validators import validate_value
from .conf import confetti_settings

CACHE_PREFIX = confetti_settings.CACHE_PREFIX
CACHE_PREFIX_ENABLED = 'is_enabled'
_CACHE_MISS = object()

def _ck(def_key, user_id=None):
    return f'{CACHE_PREFIX}:{def_key}:{user_id or "global"}'

def _is_enabled_ck(def_key, user_id=None):
    return f'{CACHE_PREFIX_ENABLED}:{def_key}:{user_id}:enabled'

def get(def_key: str, user=None, default=None):
    """
    Приоритет: user override -> global -> definition.default -> default (параметр).
    Результат кэшируется.
    """
    uid = getattr(user, 'id', None)
    cache_keys = [_ck(def_key, uid)] if uid else []
    cache_keys.append(_ck(def_key, None))
    for key in cache_keys:
        cached = cache.get(key, _CACHE_MISS)
        if cached is not _CACHE_MISS and cached is not None:
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
    Устанавливает значение с валидацией по типу. Значение None удаляет
    соответствующий override и возвращает вычисление к fallback.
    scope: None => USER если user передан, иначе GLOBAL.
    """
    defn = SettingDefinition.objects.get(key=def_key)

    if scope is None:
        scope = SettingScope.USER if user else SettingScope.GLOBAL
    if scope not in (SettingScope.USER, SettingScope.GLOBAL):
        raise ValueError(f'Недопустимое значение scope: {scope}')
    if scope == SettingScope.USER and user is None:
        raise ValueError('Для user scope необходимо передать пользователя')

    target_user = user if scope == SettingScope.USER else None
    values = SettingValue.objects.filter(
        definition=defn,
        scope=scope,
        user=target_user,
    )

    if value is None and defn.editable:
        fallback = defn.default
        if scope == SettingScope.USER:
            global_value = SettingValue.objects.filter(
                definition=defn,
                scope=SettingScope.GLOBAL,
                user__isnull=True,
            ).values_list('value', flat=True).first()
            if global_value is not None:
                fallback = global_value
        if defn.required and fallback is None:
            raise ValueError(
                f'{defn.key}: override нельзя удалить без доступного fallback'
            )

        values.delete()
        user_id = getattr(target_user, 'id', None)
        cache.delete(_ck(def_key, user_id))
        cache.delete(_is_enabled_ck(def_key, user_id))
        return None

    if not defn.editable:
        value = defn.default
    value = validate_value(defn, value)

    sv, _ = SettingValue.objects.update_or_create(
        definition=defn,
        scope=scope,
        user=target_user,
        defaults={'value': value},
    )
    cache.set(_ck(def_key, sv.user_id if sv.scope == SettingScope.USER else None), value)
    return sv

def is_enabled(flag_key: str, user=None, default=False) -> bool:
    """
    Проверяет, включена ли настройка (definition.enabled == True)
    и возвращает её логическое значение.
    Приоритет: definition.enabled=False -> user override -> global ->
    definition.enabled для bool / definition.default для остальных типов ->
    default (параметр).
    Результат кэшируется отдельно.
    """
    uid = getattr(user, 'id', None)
    user_cache_key = _is_enabled_ck(flag_key, uid) if uid else None
    global_cache_key = _is_enabled_ck(flag_key, None)

    if user_cache_key:
        cached = cache.get(user_cache_key, _CACHE_MISS)
        if cached is not _CACHE_MISS:
            return cached
    cached = cache.get(global_cache_key, _CACHE_MISS)
    if cached is not _CACHE_MISS:
        return cached

    try:
        defn = SettingDefinition.objects.get(key=flag_key)
    except SettingDefinition.DoesNotExist:
        return default

    # Если настройка выключена на уровне definition.enabled — она выключена для всех
    if not defn.enabled:
        cache.set(global_cache_key, False)
        return False

    # user override
    if uid:
        sv = SettingValue.objects.filter(
            definition=defn, scope=SettingScope.USER, user_id=uid
        ).first()
        if sv and sv.value is not None:
            result = bool(sv.value)
            cache.set(user_cache_key, result)
            return result

    # global
    gv = SettingValue.objects.filter(
        definition=defn, scope=SettingScope.GLOBAL, user__isnull=True
    ).first()
    if gv and gv.value is not None:
        result = bool(gv.value)
        cache.set(global_cache_key, result)
        return result

    # Для bool-настроек enabled является основным переключателем. default
    # синхронизируется с ним моделью, но не должен быть источником истины для
    # is_enabled (например, при чтении старых или вручную изменённых данных).
    if defn.type == SettingType.BOOL:
        result = bool(defn.enabled)
    else:
        result = bool(defn.default) if defn.default is not None else bool(default)
    cache.set(global_cache_key, result)
    return result
