from django.contrib import admin

from .models import (
    Brand,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductCategory,
    ProductImage,
    ProductVariant,
    ProductVariantAttributeValue,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("id",)


class ProductVariantAttributeValueInline(admin.TabularInline):
    model = ProductVariantAttributeValue
    extra = 0
    readonly_fields = ("attribute_value",)
    can_delete = False


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    readonly_fields = ("id", "attributes_hash", "created_at", "updated_at")
    fields = ("sku", "stock", "price_override", "promo_price", "is_active", "attributes_hash")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "slug", "created_at", "updated_at")
    list_editable = ("is_active",)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "ordering", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "slug", "created_at", "updated_at")
    list_editable = ("ordering", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "slug", "brand", "category", "price", "promo_price",
        "currency", "is_active", "is_visible", "has_variants", "created_at",
    )
    list_filter = ("is_active", "is_visible", "has_variants", "currency", "category", "brand")
    search_fields = ("name", "slug")
    ordering = ("-created_at",)
    readonly_fields = ("id", "slug", "created_at", "updated_at")
    autocomplete_fields = ["category", "brand"]
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "value")
    list_filter = ("attribute",)
    search_fields = ("value", "attribute__name")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "stock", "price_override", "promo_price", "is_active")
    list_filter = ("is_active", "product__category")
    search_fields = ("sku", "product__name")
    readonly_fields = ("id", "attributes_hash", "created_at", "updated_at")
    inlines = [ProductVariantAttributeValueInline]

    def has_delete_permission(self, request, obj=None) -> bool:
        if obj and obj.order_items.exists():
            return False
        return super().has_delete_permission(request, obj)
