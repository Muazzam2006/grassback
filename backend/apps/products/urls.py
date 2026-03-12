from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    BrandViewSet,
    ProductAttributeValueViewSet,
    ProductAttributeViewSet,
    ProductCategoryViewSet,
    ProductImageViewSet,
    ProductVariantViewSet,
    ProductViewSet,
)

router = DefaultRouter()
router.register(r"brands", BrandViewSet, basename="brands")
router.register(r"attributes", ProductAttributeViewSet, basename="attributes")
router.register(r"categories", ProductCategoryViewSet, basename="categories")
router.register(r"products", ProductViewSet, basename="products")

attribute_values_list = ProductAttributeValueViewSet.as_view(
    {"get": "list", "post": "create"}
)
attribute_values_detail = ProductAttributeValueViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

product_variants_list = ProductVariantViewSet.as_view({"get": "list", "post": "create"})
product_variants_detail = ProductVariantViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

product_images_list = ProductImageViewSet.as_view({"get": "list", "post": "create"})
product_images_detail = ProductImageViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    *router.urls,
    path(
        "attributes/<uuid:attribute_id>/values/",
        attribute_values_list,
        name="attribute-values-list",
    ),
    path(
        "attributes/<uuid:attribute_id>/values/<uuid:id>/",
        attribute_values_detail,
        name="attribute-values-detail",
    ),
    path(
        "products/<slug:product_slug>/variants/",
        product_variants_list,
        name="product-variants-list",
    ),
    path(
        "products/<slug:product_slug>/variants/<uuid:id>/",
        product_variants_detail,
        name="product-variants-detail",
    ),
    path(
        "products/<slug:product_slug>/images/",
        product_images_list,
        name="product-images-list",
    ),
    path(
        "products/<slug:product_slug>/images/<uuid:id>/",
        product_images_detail,
        name="product-images-detail",
    ),
]
