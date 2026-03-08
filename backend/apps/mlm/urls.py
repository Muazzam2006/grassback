from rest_framework.routers import DefaultRouter

from .views import StatusThresholdViewSet

router = DefaultRouter()
router.register(r"thresholds", StatusThresholdViewSet, basename="thresholds")

urlpatterns = router.urls
