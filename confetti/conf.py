from __future__ import annotations
from typing import Any
from django.conf import settings as django_settings
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.utils.module_loading import import_string

from .defaults import DEFAULTS

SETTING_NAME = 'CONFETTI'

def _import_if_str(val:Any) -> Any:
    if isinstance(val, str):
        target = val.replace(':', '.')
        return import_string(target)
    return val

class _APISettings:
    """Ленивая обертка поверх django settings с дефолтом и импортом dotted path."""
    def __init__(self, user_settings: dict[str, Any] | None = None, defaults: dict[str, Any] | None = None):
        self._user_settings = user_settings or {}
        self._defaults = defaults or {}
        self._cached: dict[str, Any] = {}

    @property
    def user_settings(self) -> dict[str, Any]:
        if not self._user_settings:
            self._user_settings = getattr(django_settings, SETTING_NAME, {}) or {}
        return self._user_settings

    def __getattr__(self, attr: str) -> Any:
        if attr in self._cached:
            return self._cached[attr]

        if attr in self.user_settings:
            val = self.user_settings[attr]
        else:
            if attr not in self._defaults:
                raise AttributeError(f'{attr} not found in {SETTING_NAME} settings')
            val = self._defaults[attr]
        try:
            val = _import_if_str(val)
        except Exception:
            pass
        self._cached[attr] = val
        return val

    def reload(self) -> None:
        self._user_settings = getattr(django_settings, SETTING_NAME, {}) or {}
        self._cached.clear()

confetti_settings = _APISettings(defaults=DEFAULTS)

@receiver(setting_changed)
def _reload_confetti(sender, setting, **kwargs):
    if setting == SETTING_NAME:
        confetti_settings.reload()