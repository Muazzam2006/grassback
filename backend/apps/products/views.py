from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import (
    Brand,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductCategory,
    ProductImage,
    ProductVariant,
)
from .permissions import IsAdminOrReadOnly, IsAdminOnly
from .serializers import (
    BrandSerializer,
    ProductAttributeSerializer,
    ProductAttributeValueSerializer,
    ProductAttributeValueWriteSerializer,
    ProductCategoryDetailSerializer,
    ProductCategoryListSerializer,
    ProductCategoryWriteSerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductImageWriteSerializer,
    ProductListSerializer,
    ProductVariantSerializer,
    ProductVariantWriteSerializer,
)


class BrandViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    serializer_class = BrandSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Brand.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminOnly()]
        return []


class ProductAttributeViewSet(viewsets.ModelViewSet):
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    serializer_class = ProductAttributeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self):
        return ProductAttribute.objects.prefetch_related("values")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminOnly()]
        return []


class ProductAttributeValueViewSet(viewsets.ModelViewSet):
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminOnly()]
        return []

    def get_queryset(self):
        return ProductAttributeValue.objects.filter(
            attribute_id=self.kwargs["attribute_id"]
        ).select_related("attribute")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductAttributeValueWriteSerializer
        return ProductAttributeValueSerializer

    def perform_create(self, serializer):
        attribute = get_object_or_404(ProductAttribute, pk=self.kwargs["attribute_id"])
        serializer.save(attribute=attribute)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["ordering", "name"]

    def get_queryset(self):
        qs = ProductCategory.objects.select_related("parent")
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductCategoryWriteSerializer
        if self.action == "retrieve":
            return ProductCategoryDetailSerializer
        return ProductCategoryListSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminOnly()]
        return []


class ProductViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "price"]
    ordering = ["-created_at"]

    def get_queryset(self):
        variant_qs = ProductVariant.objects.all().prefetch_related(
            "attribute_values__attribute_value__attribute"
        )
        if not self.request.user.is_staff:
            variant_qs = variant_qs.filter(is_active=True)

        qs = Product.objects.select_related("category", "brand").prefetch_related(
            Prefetch("variants", queryset=variant_qs),
            "images",
        )
        if self.request.user.is_staff:
            return qs

        qs = qs.filter(is_active=True, is_visible=True)
             
        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductCreateUpdateSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsAdminOrReadOnly()]
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdminOnly()]
        return []


class ProductVariantViewSet(viewsets.ModelViewSet):
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "stock", "sku"]
    ordering = ["created_at"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminOnly()]
        return []

    def get_queryset(self):
        qs = ProductVariant.objects.filter(
            product__slug=self.kwargs["product_slug"]
        ).prefetch_related("attribute_values__attribute_value__attribute")

        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True, product__is_active=True, product__is_visible=True)

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductVariantWriteSerializer
        return ProductVariantSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["product"] = get_object_or_404(Product, slug=self.kwargs["product_slug"])
        return context


class ProductImageViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["ordering"]
    ordering = ["ordering", "id"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminOnly()]
        return []

    def get_queryset(self):
        qs = ProductImage.objects.filter(product__slug=self.kwargs["product_slug"])
        if not self.request.user.is_staff:
            qs = qs.filter(product__is_active=True, product__is_visible=True)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductImageWriteSerializer
        return ProductImageSerializer

    def perform_create(self, serializer):
        product = get_object_or_404(Product, slug=self.kwargs["product_slug"])
        if serializer.validated_data.get("is_primary"):
            ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
        serializer.save(product=product)

    def perform_update(self, serializer):
        image = self.get_object()
        if serializer.validated_data.get("is_primary"):
            ProductImage.objects.filter(product=image.product, is_primary=True).exclude(
                pk=image.pk
            ).update(is_primary=False)
        serializer.save()
