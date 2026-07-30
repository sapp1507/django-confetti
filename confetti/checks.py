from django.core.checks import Error, register
from django.core.exceptions import ImproperlyConfigured

from .conf import confetti_settings


@register()
def check_confetti_response_settings(app_configs, **kwargs):
    try:
        confetti_settings.RESPONSE_STATUS_KWARG
    except ImproperlyConfigured as exc:
        return [
            Error(
                str(exc),
                id='confetti.E001',
            )
        ]
    return []
