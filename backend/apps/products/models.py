
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



class Brand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True, verbose_name=_("Name"))
    slug = models.SlugField(max_length=120, unique=True, verbose_name=_("Slug"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products_brand"
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")
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
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    slug = models.SlugField(max_length=120, unique=True, db_index=True, verbose_name=_("Slug"))
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="subcategories", verbose_name=_("Parent Category"),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    ordering = models.PositiveIntegerField(default=0, verbose_name=_("Display Order"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products_category"
        verbose_name = _("Product Category")
        verbose_name_plural = _("Product Categories")
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
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        ProductCategory, null=True, blank=True, on_delete=models.PROTECT,
        related_name="products", verbose_name=_("Category"),
    )
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.PROTECT,
        related_name="products", verbose_name=_("Brand"),
    )

    price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Base Price"),
    )
    promo_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Promo Price"),
        help_text=_("If set, overrides base price for all non-variant purchases."),
    )
    currency = models.CharField(max_length=3, default="USD")
    is_active = models.BooleanField(default=True, db_index=True)
    is_visible = models.BooleanField(default=True, db_index=True)
    has_variants = models.BooleanField(
        default=False, db_index=True,
        verbose_name=_("Has Variants"),
        help_text=_("True when product has SKU-level variants."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products_product"
        ordering = ["-created_at"]
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="product_price_gte_0"),
            models.CheckConstraint(
                condition=models.Q(promo_price__isnull=True) | models.Q(promo_price__gte=0),
                name="prod_promo_price_gte_0",
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
    )
    image_url = models.URLField(max_length=500, verbose_name=_("Image URL"))
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False, db_index=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "products_image"
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")
        ordering = ["ordering"]
        constraints = [
            # Only one primary image per product
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_product",
            ),
        ]

    def __str__(self) -> str:
        return f"Image({self.product.name}, primary={self.is_primary})"


class ProductAttribute(models.Model):
    """Attribute dimension: Color, Size, Material, etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Name"))

    class Meta:
        db_table = "products_attribute"
        verbose_name = _("Product Attribute")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ProductAttributeValue(models.Model):
    """Concrete attribute value: Red, XL, Cotton, etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(
        ProductAttribute, on_delete=models.CASCADE, related_name="values",
    )
    value = models.CharField(max_length=100, verbose_name=_("Value"))

    class Meta:
        db_table = "products_attribute_value"
        verbose_name = _("Attribute Value")
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
    )
    sku = models.CharField(max_length=100, unique=True, db_index=True, verbose_name=_("SKU"))
    stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Stock"),
        help_text=_("Available units.  Updated atomically via F() expressions."),
    )
    price_override = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Price Override"),
        help_text=_("If set, replaces product base price for this SKU."),
    )
    promo_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Promo Price Override"),
    )
    is_active = models.BooleanField(default=True, db_index=True)

    attributes_hash = models.CharField(
        max_length=64,
        editable=False,
        db_index=True,
        verbose_name=_("Attributes Hash"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products_variant"
        verbose_name = _("Product Variant")
        verbose_name_plural = _("Product Variants")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attributes_hash"],
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
        return f"Variant({self.product.name}, SKU={self.sku})"

    def save(self, *args, **kwargs):
        if not self.attributes_hash:
            # If creating via standard forms/admin, attribute links are added AFTER
            # the variant is created. We initialize with an empty hash, and update
            # it later if attributes are attached.
            self.attributes_hash = _compute_attribute_hash([])
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
    )
    attribute_value = models.ForeignKey(
        ProductAttributeValue, on_delete=models.PROTECT, related_name="variant_links",
    )

    class Meta:
        db_table = "products_variant_attribute_value"
        verbose_name = _("Variant Attribute Value")
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