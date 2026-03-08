from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # JWT authentication
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Domain API routes  (C-2: previously only admin/ was registered)
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.products.urls")),        # → /api/v1/products/ + /api/v1/categories/
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.bonuses.urls")),
    path("api/v1/", include("apps.withdrawals.urls")),     # → /api/v1/withdrawals/
    path("api/v1/mlm/", include("apps.mlm.urls")),         # → /api/v1/mlm/thresholds/
    path("api/v1/", include("apps.delivery.urls")),        # → /api/v1/delivery/ + addresses + couriers
    path("api/v1/", include("apps.reservations.urls")),    # → /api/v1/reservations/

    # OpenAPI schema & Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
