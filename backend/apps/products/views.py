from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Product, ProductCategory, ProductVariant
from .permissions import IsAdminOrReadOnly, IsAdminOnly
from .serializers import (
    ProductCategoryDetailSerializer,
    ProductCategoryListSerializer,
    ProductCategoryWriteSerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


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
        variant_qs = ProductVariant.objects.all()
        if not self.request.user.is_staff:
            variant_qs = variant_qs.filter(is_active=True)

        qs = Product.objects.select_related("category", "brand").prefetch_related(
            Prefetch("variants", queryset=variant_qs)
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
