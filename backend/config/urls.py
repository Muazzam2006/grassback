from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

try:
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )
except Exception:
    BlacklistedToken = None
    OutstandingToken = None


admin.site.site_header = "Администрирование Grass MLM"
admin.site.site_title = "Админ-панель"
admin.site.index_title = "Панель управления"

for model in (OutstandingToken, BlacklistedToken):
    if model is not None:
        try:
            admin.site.unregister(model)
        except NotRegistered:
            pass

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass


urlpatterns = [
                  
    path("admin/", admin.site.urls),

                        
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

                                                                     
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.products.urls")),                                                   
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.bonuses.urls")),
    path("api/v1/", include("apps.withdrawals.urls")),                             
    path("api/v1/mlm/", include("apps.mlm.urls")),                                    
    path("api/v1/", include("apps.delivery.urls")),                                                    
    path("api/v1/", include("apps.reservations.urls")),                             

                                 
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
