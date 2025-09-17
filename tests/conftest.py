# tests/conftest.py
import django
import pytest
from django.conf import settings as dj_settings

def pytest_configure():
    if not dj_settings.configured:
        dj_settings.configure(
            SECRET_KEY="test-secret",
            DEBUG=True,
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.admin",
                "django.contrib.messages",
                "confetti",
            ],
            MIDDLEWARE=[
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
            ],
            ROOT_URLCONF="tests.urls",
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "confetti-tests",
                }
            },
            TEMPLATES=[{
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ]
                },
            }],
        )
    django.setup()

    # дефолтные сид-данные для тестов
    dj_settings.CONFETTI = {
        "AUTO_SEED": True,
        "SEED_CATEGORIES": [
            {"code": "scheduler", "title": "Планировщик"},
            {"code": "ui", "title": "Интерфейс"},
        ],
        "SEED_DEFINITIONS": [
            {"key": "feature.jobs", "type": "bool", "category": "scheduler", "title": "Jobs", "default": True},
            {
                "key": "ui.theme",
                "type": "choice",
                "category": "ui",
                "title": "Theme",
                "default": "light",
                "choices": [{"value": "light", "label": "Light"}, {"value": "dark", "label": "Dark"}],
            },
        ],
    }

@pytest.fixture
def user(django_user_model, db):
    return django_user_model.objects.create_user(username="u", email="u@example.com", password="p")

@pytest.fixture(autouse=True)
def _clear_cache_and_reload_confetti(settings):
    from django.core.cache import cache
    cache.clear()
    from confetti.conf import confetti_settings
    confetti_settings.reload()
    yield
    cache.clear()
    confetti_settings.reload()
