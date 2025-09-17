from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ConfettiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'confetti'
    verbose_name = 'Confetti settings'

    def ready(self):
        from .signals import connect_confetti_signals
        connect_confetti_signals()

        from .seed import seed_from_settings
        def _seed(*args, **kwargs):
            try:
                from .conf import confetti_settings
                if confetti_settings.AUTO_SEED:
                    seed_from_settings()
            except Exception:
                pass

        post_migrate.connect(_seed, dispatch_uid='django-confetti-seed-post-migrate')
