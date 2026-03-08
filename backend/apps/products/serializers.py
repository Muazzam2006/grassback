from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils.text import slugify
from rest_framework import serializers

from .models import Brand, Product, ProductCategory, ProductVariant

_SLUG_MAX_RETRIES = 20


class FlexiblePkOrSlugRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, *args, slug_field: str = "slug", **kwargs):
        self.slug_field = slug_field
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        if data in (None, ""):
            if self.allow_null:
                return None
            self.fail("required")

        try:
            return super().to_internal_value(data)
        except Exception as pk_error:
            if isinstance(data, str):
                queryset = self.get_queryset()
                if queryset is not None:
                    try:
                        return queryset.get(**{self.slug_field: data})
                    except Exception:
                        raise pk_error
            raise pk_error


class ProductCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "parent", "ordering", "is_active"]
        read_only_fields = ["id", "slug"]


class ProductCategoryDetailSerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "parent", "ordering", "is_active",
                  "subcategories", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_subcategories(self, obj):
        qs = obj.subcategories.filter(is_active=True)
        return ProductCategoryListSerializer(qs, many=True).data


class ProductCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["name", "parent", "ordering", "is_active"]

    def validate_parent(self, value):
        instance = self.instance
        if instance and value and str(value.pk) == str(instance.pk):
            raise serializers.ValidationError("A category cannot be its own parent.")
        return value


class ProductCategoryInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class BrandInlineSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)


class ProductVariantInlineSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "effective_price"]
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    category = ProductCategoryInlineSerializer(read_only=True)
    brand = BrandInlineSerializer(read_only=True)
    variants = ProductVariantInlineSerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "price", "promo_price", "effective_price",
            "currency", "has_variants", "variants", "category", "brand", "created_at",
        ]
        read_only_fields = fields


class ProductDetailSerializer(serializers.ModelSerializer):
    category = ProductCategoryInlineSerializer(read_only=True)
    brand = BrandInlineSerializer(read_only=True)
    variants = ProductVariantInlineSerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description",
            "price", "promo_price", "effective_price",
            "currency", "has_variants", "variants",
            "category", "brand",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    category = FlexiblePkOrSlugRelatedField(
        queryset=ProductCategory._default_manager.all(),
        required=False,
        allow_null=True,
    )
    brand = FlexiblePkOrSlugRelatedField(
        queryset=Brand._default_manager.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "description",
            "price", "promo_price",
            "currency", "category", "brand",
            "is_active", "is_visible", "has_variants",
        ]
        read_only_fields = ["id"]

    def validate_price(self, value: Decimal) -> Decimal:
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Price must be non-negative.")
        return value

    def validate_promo_price(self, value: Decimal | None) -> Decimal | None:
        if value is not None and value < Decimal("0.00"):
            raise serializers.ValidationError("Promo price must be non-negative.")
        return value

    def validate_currency(self, value: str) -> str:
        value = value.upper().strip()
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter ISO 4217 code.")
        return value

    def validate_category(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Cannot assign an inactive category to a product.")
        return value
