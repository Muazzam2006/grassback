from rest_framework.routers import DefaultRouter

from .views import BonusViewSet

router = DefaultRouter()
router.register(r"bonuses", BonusViewSet, basename="bonus")

urlpatterns = router.urls
