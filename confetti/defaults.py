from __future__ import annotations

DEFAULTS = {
    'FRONTEND_CACHE_TIMEOUT': 300, # секунды
    'FRONTEND_CACHE_PREFIX': 'confetti:v1:frontend',
    'CACHE_PREFIX': 'confetti:v1',
    # Функция/класс ответа: можно передать объектом или строкой
    'RESPONSE_METHOD': 'confetti.responses.default_response',
    'AUTO_SEED': True,
    'SEED_CATEGORIES': [], # [{'code': 'scheduler', 'title': 'Планировщик'}]
    'SEED_DEFINITIONS': [],
    # {
    #     'key': 'feature.scheduler.enable_jobs',
    #     'type': "bool',
    #     'category': 'scheduler',
    #     'title': 'Включить планировщик',
    #     'default': True,
    # },
}