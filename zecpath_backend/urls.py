"""
URL configuration for zecpath_backend project.

The `urlpatterns` list routes URLs to views.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


class LoginThrottle(AnonRateThrottle):
    scope = "login"


urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # ZecPath API
    path("api/", include("accounts.urls")),

    # JWT Authentication
    path(
        "api/token/",
        TokenObtainPairView.as_view(
            throttle_classes=[LoginThrottle]
        ),
        name="token_obtain_pair",
    ),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # ============================================================
    # API DOCUMENTATION - SWAGGER / OPENAPI
    # ============================================================

    # OpenAPI schema
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema"
        ),
        name="swagger-ui",
    ),

    # ReDoc
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema"
        ),
        name="redoc",
    ),
]


# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )