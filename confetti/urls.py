from django.core.exceptions import ImproperlyConfigured
from django.urls import path

try:
    from .views import SettingDetailView, SettingFrontendView, SettingListView
except ModuleNotFoundError as exc:
    if exc.name == 'rest_framework':
        raise ImproperlyConfigured(
            "Для подключения confetti.urls установите django-confetti[drf]."
        ) from exc
    raise

app_name = 'django_confetti'

urlpatterns = [
    path('settings/', SettingListView.as_view(), name='settings-list'),
    path('settings/frontend/', SettingFrontendView.as_view(), name='settings-frontend'),
    path('settings/<str:key>/', SettingDetailView.as_view(), name='settings-detail'),
]
