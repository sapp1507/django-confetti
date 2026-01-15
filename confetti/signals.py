from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import SettingValue, SettingDefinition, SettingScope
from .conf import confetti_settings
from .api import _ck, _is_enabled_ck


@receiver([post_save, post_delete], sender=SettingValue)
def purge_value_cache(sender, instance, **kwargs):
    """
    Когда меняется конкретное значение (глобальное или пользовательское) —
    инвалидируем соответствующий кэш-ключ.
    """
    cache.delete(_ck(instance.definition.key,
                     instance.user_id if instance.scope == SettingScope.USER else None))
    cache.delete(_is_enabled_ck(instance.definition.key,
                                instance.user_id if instance.scope == SettingScope.USER else None))


@receiver([post_save, post_delete], sender=SettingDefinition)
def purge_definition_cache(sender, instance, **kwargs):
    """
    Когда меняется определение настройки:
      - удаляем глобальный кэш ключ
      - и все ключи для пользовательских оверрайдов этой дефиниции
    """
    cache.delete(_ck(instance.key), None)
    cache.delete(_is_enabled_ck(instance.key), None)
    user_vals =SettingValue.objects.filter(
        definition=instance,
        scope=SettingScope.USER,
    ).only('user_id')
    for sv in user_vals:
        cache.delete(_ck(instance.key, sv.user_id))
        cache.delete(_is_enabled_ck(instance.key, sv.user_id))
    if instance.frontend:
        cache.delete(confetti_settings.FRONTEND_CACHE_PREFIX)

def connect_confetti_signals() -> None:
    """
    Вызывается из apps.py:ready() для гарантированного подключения ресиверов,
    если модуль signals подгружается лениво.
    """
    # сам факт импорта/вызова оставляет зарегистрированные @receiver.
    # ничего больше делать не нужно.
    return None
