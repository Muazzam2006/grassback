from rest_framework.routers import DefaultRouter

from .views import CourierViewSet, DeliveryAddressViewSet, OrderDeliveryViewSet

router = DefaultRouter()
router.register(r"delivery/addresses", DeliveryAddressViewSet, basename="delivery-addresses")
router.register(r"delivery/couriers", CourierViewSet, basename="couriers")
router.register(r"delivery", OrderDeliveryViewSet, basename="deliveries")

urlpatterns = router.urls
