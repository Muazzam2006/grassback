import hashlib
import uuid
from decimal import Decimal

from django.db import IntegrityError, models, transaction
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

_SLUG_MAX_RETRIES = 20


def _compute_attribute_hash(attribute_value_ids: list) -> str:

    canonical = ",".join(sorted(str(vid) for vid in attribute_value_ids))
    return hashlib.sha256(canonical.encode()).hexdigest()


_EMPTY_ATTRIBUTES_HASH = _compute_attribute_hash([])



class Brand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True, verbose_name=_("Название"))
    slug = models.SlugField(max_length=120, unique=True, verbose_name=_("ЧПУ (Slug)"))
    description = models.TextField(blank=True, verbose_name=_("Описание"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Активен"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создан"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлен"))

    class Meta:
        db_table = "products_brand"
        verbose_name = _("Бренд")
        verbose_name_plural = _("Бренды")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            for attempt in range(1, _SLUG_MAX_RETRIES + 1):
                self.slug = base if attempt == 1 else f"{base}-{attempt}"
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    continue
            raise RuntimeError("Could not generate unique slug for brand.")
        return super().save(*args, **kwargs)


class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Название"))
    slug = models.SlugField(max_length=120, unique=True, db_index=True, verbose_name=_("ЧПУ (Slug)"))
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="subcategories", verbose_name=_("Родительская категория"),
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Активна"))
    ordering = models.PositiveIntegerField(default=0, verbose_name=_("Порядок отображения"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создана"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлена"))

    class Meta:
        db_table = "products_category"
        verbose_name = _("Категория товара")
        verbose_name_plural = _("Категории товаров")
        ordering = ["ordering", "name"]
        indexes = [
            models.Index(fields=["parent", "is_active"], name="category_parent_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(parent__isnull=True) | ~models.Q(parent=models.F("pk")),
                name="category_not_self_parent",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            for attempt in range(1, _SLUG_MAX_RETRIES + 1):
                self.slug = base if attempt == 1 else f"{base}-{attempt}"
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    continue
            raise RuntimeError("Could not generate unique slug for category.")
        return super().save(*args, **kwargs)


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Название"))
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_("ЧПУ (Slug)"))
    description = models.TextField(blank=True, verbose_name=_("Описание"))

    category = models.ForeignKey(
        ProductCategory, null=True, blank=True, on_delete=models.PROTECT,
        related_name="products", verbose_name=_("Категория"),
    )
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.PROTECT,
        related_name="products", verbose_name=_("Бренд"),
    )

    price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Базовая цена"),
    )
    promo_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Цена по акции"),
        help_text=_("Если указано, переопределяет базовую цену."),
    )
    currency = models.CharField(max_length=3, default="TJS", verbose_name=_("Валюта"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Активен"))
    is_visible = models.BooleanField(default=True, db_index=True, verbose_name=_("Показывать"))
    stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Остаток"),
        help_text=_("Доступное количество для товаров без вариантов."),
    )
    has_variants = models.BooleanField(
        default=False, db_index=True,
        verbose_name=_("Есть варианты"),
        help_text=_("Отметьте, если у товара есть варианты с разными артикулами (SKU)."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создан"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлен"))

    class Meta:
        db_table = "products_product"
        ordering = ["-created_at"]
        verbose_name = _("Товар")
        verbose_name_plural = _("Товары")
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="product_price_gte_0"),
            models.CheckConstraint(
                condition=models.Q(promo_price__isnull=True) | models.Q(promo_price__gte=0),
                name="prod_promo_price_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name="prod_stock_gte_0",
            ),
        ]
        indexes = [
            models.Index(
                fields=["category", "is_active", "is_visible"],
                name="prod_cat_active_visible_idx",
            ),
            models.Index(
                fields=["brand", "is_active"],
                name="product_brand_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def effective_price(self) -> Decimal:
        return self.promo_price if self.promo_price is not None else self.price

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            for attempt in range(1, _SLUG_MAX_RETRIES + 1):
                self.slug = base if attempt == 1 else f"{base}-{attempt}"
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    continue
            raise RuntimeError("Could not generate unique slug for product.")
        return super().save(*args, **kwargs)


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images",
        verbose_name=_("Товар"),
    )
    image = models.ImageField(upload_to="products/images/", null=True, blank=True, verbose_name=_("Изображение (файл)"))
    image_url = models.URLField(max_length=500, null=True, blank=True, verbose_name=_("URL-адрес изображения"))
    alt_text = models.CharField(max_length=255, blank=True, verbose_name=_("Альтернативный текст"))
    is_primary = models.BooleanField(default=False, db_index=True, verbose_name=_("Основное"))
    ordering = models.PositiveIntegerField(default=0, verbose_name=_("Порядок"))

    class Meta:
        db_table = "products_image"
        verbose_name = _("Изображение товара")
        verbose_name_plural = _("Изображения товаров")
        ordering = ["ordering"]
        constraints = [
                                                
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_product",
            ),
        ]

    def __str__(self) -> str:
        return f"Image({self.product.name}, primary={self.is_primary})"


class ProductAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название"))

    class Meta:
        db_table = "products_attribute"
        verbose_name = _("Характеристика товара")
        verbose_name_plural = _("Характеристики товаров")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ProductAttributeValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(
        ProductAttribute, on_delete=models.CASCADE, related_name="values",
        verbose_name=_("Характеристика"),
    )
    value = models.CharField(max_length=100, verbose_name=_("Значение"))

    class Meta:
        db_table = "products_attribute_value"
        verbose_name = _("Значение характеристики")
        verbose_name_plural = _("Значения характеристик")
        ordering = ["attribute", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "value"],
                name="unique_attribute_value_per_attribute",
            ),
        ]
        indexes = [
            models.Index(fields=["attribute"], name="attr_value_attribute_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants",
        verbose_name=_("Товар"),
    )
    image = models.ImageField(upload_to="products/variants/", null=True, blank=True, verbose_name=_("Изображение варианта"))
    sku = models.CharField(max_length=100, db_index=True, verbose_name=_("Артикул (SKU)"))
    stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Остаток"),
        help_text=_("Доступное количество."),
    )
    price_override = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Переопределение цены"),
        help_text=_("Если указано, заменяет базовую цену товара для этого варианта."),
    )
    promo_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Переопределение цены по акции"),
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Активен"))

    attributes_hash = models.CharField(
        max_length=64,
        editable=False,
        db_index=True,
        verbose_name=_("Хэш атрибутов"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создан"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлен"))

    class Meta:
        db_table = "products_variant"
        verbose_name = _("Вариант товара")
        verbose_name_plural = _("Варианты товара")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "sku"],
                name="unique_variant_sku_per_product",
            ),
            models.UniqueConstraint(
                fields=["product", "attributes_hash"],
                condition=~models.Q(attributes_hash=_EMPTY_ATTRIBUTES_HASH),
                name="unique_variant_per_product_attributes",
            ),
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name="variant_stock_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(price_override__isnull=True) | models.Q(price_override__gte=0),
                name="variant_price_override_gte_0_or_null",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "is_active"], name="variant_product_active_idx"),
        ]

    def __str__(self) -> str:
        return f"Артикул: {self.sku}"

    def save(self, *args, **kwargs):
        if not self.attributes_hash:
            self.attributes_hash = _EMPTY_ATTRIBUTES_HASH
        super().save(*args, **kwargs)

    @property
    def effective_price(self) -> Decimal:
        if self.promo_price is not None:
            return self.promo_price
        if self.price_override is not None:
            return self.price_override
        return self.product.effective_price


class ProductVariantAttributeValue(models.Model):
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="attribute_values",
        verbose_name=_("Вариант"),
    )
    attribute_value = models.ForeignKey(
        ProductAttributeValue, on_delete=models.PROTECT, related_name="variant_links",
        verbose_name=_("Значение характеристики"),
    )

    class Meta:
        db_table = "products_variant_attribute_value"
        verbose_name = _("Значение характеристики варианта")
        verbose_name_plural = _("Значения характеристик вариантов")
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "attribute_value"],
                name="unique_attr_value_per_variant",
            ),
        ]
        indexes = [
            models.Index(fields=["variant"], name="vav_variant_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.variant.sku} — {self.attribute_value}"
