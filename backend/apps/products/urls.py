from rest_framework.routers import DefaultRouter

from .views import ProductCategoryViewSet, ProductViewSet

router = DefaultRouter()
# M-2: explicit basename since ViewSet has no class-level queryset.
router.register(r"categories", ProductCategoryViewSet, basename="categories")
router.register(r"products", ProductViewSet, basename="products")

urlpatterns = router.urls
