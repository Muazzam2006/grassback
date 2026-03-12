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

Brand._meta.verbose_name = "Бренд"
Brand._meta.verbose_name_plural = "Бренды"
ProductCategory._meta.verbose_name = "Категория товара"
ProductCategory._meta.verbose_name_plural = "Категории товаров"
Product._meta.verbose_name = "Товар"
Product._meta.verbose_name_plural = "Товары"
ProductAttribute._meta.verbose_name = "Характеристика товара"
ProductAttribute._meta.verbose_name_plural = "Характеристики товара"
ProductAttributeValue._meta.verbose_name = "Значение характеристики"
ProductAttributeValue._meta.verbose_name_plural = "Значения характеристик"
ProductVariant._meta.verbose_name = "Вариант товара"
ProductVariant._meta.verbose_name_plural = "Варианты товара"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantAttributeValueInline(admin.TabularInline):
    model = ProductVariantAttributeValue
    extra = 0
    readonly_fields = ("attribute_value",)
    can_delete = False


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 0
    fields = ("value",)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("sku", "stock", "price_override", "promo_price", "is_active")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name_display", "is_active_display", "created_at_display")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("slug", "created_at", "updated_at")

    @admin.display(description="Название", ordering="name")
    def name_display(self, obj: Brand):
        return obj.name

    @admin.display(boolean=True, description="Активен", ordering="is_active")
    def is_active_display(self, obj: Brand):
        return obj.is_active

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Brand):
        return obj.created_at


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name_display",
        "parent_display",
        "ordering_display",
        "is_active_display",
    )
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    readonly_fields = ("slug", "created_at", "updated_at")

    @admin.display(description="Название", ordering="name")
    def name_display(self, obj: ProductCategory):
        return obj.name

    @admin.display(description="Родительская категория", ordering="parent")
    def parent_display(self, obj: ProductCategory):
        return obj.parent

    @admin.display(description="Порядок", ordering="ordering")
    def ordering_display(self, obj: ProductCategory):
        return obj.ordering

    @admin.display(boolean=True, description="Активна", ordering="is_active")
    def is_active_display(self, obj: ProductCategory):
        return obj.is_active


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name_display",
        "brand_display",
        "category_display",
        "price_display",
        "promo_price_display",
        "currency_display",
        "is_active_display",
        "is_visible_display",
        "has_variants_display",
        "created_at_display",
    )
    list_filter = ("is_active", "is_visible", "has_variants", "currency", "category", "brand")
    search_fields = ("name", "slug")
    ordering = ("-created_at",)
    readonly_fields = ("slug", "created_at", "updated_at")
    autocomplete_fields = ["category", "brand"]
    inlines = [ProductImageInline, ProductVariantInline]

    @admin.display(description="Название", ordering="name")
    def name_display(self, obj: Product):
        return obj.name

    @admin.display(description="Бренд", ordering="brand")
    def brand_display(self, obj: Product):
        return obj.brand

    @admin.display(description="Категория", ordering="category")
    def category_display(self, obj: Product):
        return obj.category

    @admin.display(description="Базовая цена", ordering="price")
    def price_display(self, obj: Product):
        return obj.price

    @admin.display(description="Цена по акции", ordering="promo_price")
    def promo_price_display(self, obj: Product):
        return obj.promo_price

    @admin.display(description="Валюта", ordering="currency")
    def currency_display(self, obj: Product):
        return obj.currency

    @admin.display(boolean=True, description="Активен", ordering="is_active")
    def is_active_display(self, obj: Product):
        return obj.is_active

    @admin.display(boolean=True, description="Показывать", ordering="is_visible")
    def is_visible_display(self, obj: Product):
        return obj.is_visible

    @admin.display(boolean=True, description="Есть варианты", ordering="has_variants")
    def has_variants_display(self, obj: Product):
        return obj.has_variants

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Product):
        return obj.created_at


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("name_display",)
    search_fields = ("name",)
    inlines = [ProductAttributeValueInline]

    @admin.display(description="Характеристика", ordering="name")
    def name_display(self, obj: ProductAttribute):
        return obj.name


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute_display", "value_display")
    list_filter = ("attribute",)
    search_fields = ("value", "attribute__name")

    @admin.display(description="Характеристика", ordering="attribute__name")
    def attribute_display(self, obj: ProductAttributeValue):
        return obj.attribute

    @admin.display(description="Значение", ordering="value")
    def value_display(self, obj: ProductAttributeValue):
        return obj.value

    def get_model_perms(self, request):
        return {}


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "sku_display",
        "product_display",
        "stock_display",
        "price_override_display",
        "promo_price_display",
        "is_active_display",
    )
    list_filter = ("is_active", "product__category")
    search_fields = ("sku", "product__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductVariantAttributeValueInline]

    @admin.display(description="Артикул", ordering="sku")
    def sku_display(self, obj: ProductVariant):
        return obj.sku

    @admin.display(description="Товар", ordering="product__name")
    def product_display(self, obj: ProductVariant):
        return obj.product

    @admin.display(description="Остаток", ordering="stock")
    def stock_display(self, obj: ProductVariant):
        return obj.stock

    @admin.display(description="Цена варианта", ordering="price_override")
    def price_override_display(self, obj: ProductVariant):
        return obj.price_override

    @admin.display(description="Акционная цена", ordering="promo_price")
    def promo_price_display(self, obj: ProductVariant):
        return obj.promo_price

    @admin.display(boolean=True, description="Активен", ordering="is_active")
    def is_active_display(self, obj: ProductVariant):
        return obj.is_active

    def get_model_perms(self, request):
        return {}

    def has_delete_permission(self, request, obj=None) -> bool:
        if obj and obj.order_items.exists():
            return False
        return super().has_delete_permission(request, obj)
