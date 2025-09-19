from django.urls import path
from .views import SettingListView, SettingDetailView, SettingFrontendView

app_name = 'django_confetti'

urlpatterns = [
    path('settings/', SettingListView.as_view(), name='settings-list'),
    path('settings/frontend/', SettingFrontendView.as_view(), name='settings-frontend'),
    path('settings/<str:key>/', SettingDetailView.as_view(), name='settings-detail'),
]
