import pytest
from django.contrib.auth import get_user_model

@pytest.fixture
def user(db):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='user', email='user@example.com')
    return user

@pytest.fixture(autouse=True)
def _clear_cache_and_reload_confetti(settings):
    from django.core.cache import cache
    cache.clear()
    from confetti.conf import confetti_settings
    confetti_settings.reload()
    yield
    cache.clear()
    confetti_settings.reload()
