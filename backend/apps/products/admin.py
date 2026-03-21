from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.contrib.forms.widgets import WysiwygWidget

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
from .forms import ProductAdminForm, ProductVariantAdminForm
from django.utils.html import format_html

Brand._meta.verbose_name = "Бренд"
Brand._meta.verbose_name_plural = "Бренды"
ProductCategory._meta.verbose_name = "Категория товара"
ProductCategory._meta.verbose_name_plural = "Категории товаров"
Product._meta.verbose_name = "Товар"
Product._meta.verbose_name_plural = "Товары"
ProductAttribute._meta.verbose_name = "Параметр"
ProductAttribute._meta.verbose_name_plural = "Параметры"
ProductAttributeValue._meta.verbose_name = "Значение характеристики"
ProductAttributeValue._meta.verbose_name_plural = "Значения характеристик"
ProductVariant._meta.verbose_name = "Вариант товара"
ProductVariant._meta.verbose_name_plural = "Варианты товара"

Brand._meta.get_field("is_active").verbose_name = "Активен"

ProductCategory._meta.get_field("is_active").verbose_name = "Активна"
ProductCategory._meta.get_field("parent").verbose_name = "Родительская категория"

Product._meta.get_field("is_active").verbose_name = "Доступен к продаже"
Product._meta.get_field("is_visible").verbose_name = "Показывать в каталоге"
Product._meta.get_field("has_variants").verbose_name = "Есть варианты"
Product._meta.get_field("currency").verbose_name = "Валюта"
Product._meta.get_field("category").verbose_name = "Категория"
Product._meta.get_field("brand").verbose_name = "Бренд"
Product._meta.get_field("attribute_values").verbose_name = "Характеристики товара"

ProductAttributeValue._meta.get_field("attribute").verbose_name = "Характеристика"

ProductVariant._meta.get_field("is_active").verbose_name = "Активен"


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "image_url", "alt_text", "is_primary", "ordering", "image_preview")
    readonly_fields = ("image_preview",)

    @admin.display(description="Предпросмотр")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img class="image-preview" src="{}" style="max-width: 200px; max-height: 200px; border-radius: 6px; object-fit: contain;" />', obj.image.url)
        elif obj.image_url:
            return format_html('<img class="image-preview" src="{}" style="max-width: 200px; max-height: 200px; border-radius: 6px; object-fit: contain;" />', obj.image_url)
        return "-"


class ProductVariantAttributeValueInline(TabularInline):
    model = ProductVariantAttributeValue
    extra = 0
    readonly_fields = ("attribute_value",)
    can_delete = False


class ProductAttributeValueInline(TabularInline):
    model = ProductAttributeValue
    extra = 0
    fields = ("value",)


class ProductVariantInline(StackedInline):
    model = ProductVariant
    form = ProductVariantAdminForm
    extra = 0
    fields = (
        ("sku", "image_preview"),
        "image",
        "stock",
        ("price_override", "promo_price"),
        "attribute_value_ids",
        "is_active",
    )
    readonly_fields = ("image_preview",)

    @admin.display(description="Предпросмотр")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img class="image-preview" src="{}" style="max-width: 200px; max-height: 200px; border-radius: 6px; object-fit: contain;" />', obj.image.url)
        return "-"


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ("image_preview", "name_display", "is_active_display", "created_at_display")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("image_preview",)
    exclude = ("slug",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name", "image_preview"),
                    "image",
                    "description",
                    "is_active",
                )
            },
        ),
    )

    @admin.display(description="Предпросмотр")
    def image_preview(self, obj: Brand):
        if obj.image:
            return format_html(
                '<img class="image-preview" src="{}" style="max-width: 80px; max-height: 80px; border-radius: 6px; object-fit: cover;" />',
                obj.image.url,
            )
        return "-"

    @admin.display(description="Название", ordering="name")
    def name_display(self, obj: Brand):
        return obj.name

    @admin.display(boolean=True, description="Активен", ordering="is_active")
    def is_active_display(self, obj: Brand):
        return obj.is_active

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Brand):
        return obj.created_at

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = WysiwygWidget
        return super().formfield_for_dbfield(db_field, **kwargs)


@admin.register(ProductCategory)
class ProductCategoryAdmin(ModelAdmin):
    list_display = (
        "image_preview",
        "name_display",
        "parent_display",
        "ordering_display",
        "is_active_display",
    )
    readonly_fields = ("image_preview",)
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    exclude = ("slug",)

    @admin.display(description="Предпросмотр")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img class="image-preview" src="{}" style="max-height: 50px; border-radius: 4px;" />', obj.image.url)
        return "-"

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs.setdefault("empty_label", "Выберите значение")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductAdminForm

    class Media:
        js = ("js/product_admin.js", "js/product_attributes_admin.js")

    list_display = (
        "name_display",
        "brand_display",
        "category_display",
        "price_display",
        "promo_price_display",
        "stock_display",
        "is_active_display",
        "is_visible_display",
        "has_variants_display",
        "created_at_display",
    )
    list_filter = ("is_active", "is_visible", "has_variants", "category", "brand")
    search_fields = ("name", "slug")
    ordering = ("-created_at",)
    exclude = ("slug", "currency", "attribute_values")
    autocomplete_fields = ["category", "brand"]
    inlines = [ProductImageInline, ProductVariantInline]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "category",
                    "brand",
                    ("price", "promo_price"),
                    "description",
                    ("stock", "has_variants"),
                    ("is_active", "is_visible"),
                )
            },
        ),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = WysiwygWidget
        return super().formfield_for_dbfield(db_field, **kwargs)

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

    @admin.display(description="Остаток", ordering="stock")
    def stock_display(self, obj: Product):
        return obj.stock

    @admin.display(boolean=True, description="Доступен к продаже", ordering="is_active")
    def is_active_display(self, obj: Product):
        return obj.is_active

    @admin.display(boolean=True, description="Показывать в каталоге", ordering="is_visible")
    def is_visible_display(self, obj: Product):
        return obj.is_visible

    @admin.display(boolean=True, description="Есть варианты", ordering="has_variants")
    def has_variants_display(self, obj: Product):
        return obj.has_variants

    @admin.display(description="Создан", ordering="created_at")
    def created_at_display(self, obj: Product):
        return obj.created_at


@admin.register(ProductAttribute)
class ProductAttributeAdmin(ModelAdmin):
    list_display = ("name_display",)
    search_fields = ("name",)
    inlines = [ProductAttributeValueInline]

    @admin.display(description="Характеристика", ordering="name")
    def name_display(self, obj: ProductAttribute):
        return obj.name


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(ModelAdmin):
    list_display = ("attribute_display", "value_display")
    list_filter = ("attribute",)
    search_fields = ("value", "attribute__name")

    @admin.display(description="Характеристика", ordering="attribute__name")
    def attribute_display(self, obj: ProductAttributeValue):
        return obj.attribute

    @admin.display(description="Значение", ordering="value")
    def value_display(self, obj: ProductAttributeValue):
        return obj.value

    # def get_model_perms(self, request):
    #     return {}


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    form = ProductVariantAdminForm

    class Media:
        js = ("js/product_attributes_admin.js",)

    list_display = (
        "sku_display",
        "image_preview_list",
        "product_display",
        "stock_display",
        "price_override_display",
        "promo_price_display",
        "is_active_display",
    )
    list_filter = ("is_active", "product__category")
    search_fields = ("sku", "product__name")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "product",
                    "sku",
                    "image",
                    "stock",
                    ("price_override", "promo_price"),
                    "attribute_value_ids",
                    "is_active",
                )
            },
        ),
    )

    @admin.display(description="Изображение")
    def image_preview_list(self, obj: ProductVariant):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 40px; border-radius: 4px;" />', obj.image.url)
        return "-"

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
