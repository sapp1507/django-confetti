from django.urls import path, include

urlpatterns = [
    path("api/confetti/", include(("confetti.urls", "confetti"), namespace="confetti")),
]
