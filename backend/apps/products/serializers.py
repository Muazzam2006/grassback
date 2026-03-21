from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import (
    Brand,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductCategory,
    ProductImage,
    ProductVariant,
    ProductVariantAttributeValue,
    _compute_attribute_hash,
)


def _resolve_media_or_external_url(request, image_field, image_url):
    if image_field:
        try:
            url = image_field.url
        except ValueError:
            url = ""
        if url:
            return request.build_absolute_uri(url) if request else url
    return image_url

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
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "parent", "ordering", "is_active", "image_url"]
        read_only_fields = ["id", "slug"]

    def get_image_url(self, obj):
        return _resolve_media_or_external_url(self.context.get("request"), obj.image, None)


class ProductCategoryDetailSerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "parent", "ordering", "is_active",
                  "image_url", "subcategories", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_image_url(self, obj):
        return _resolve_media_or_external_url(self.context.get("request"), obj.image, None)

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
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        return _resolve_media_or_external_url(self.context.get("request"), obj.image, None)


class ProductVariantInlineSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "effective_price", "image_url"]
        read_only_fields = fields

    def get_image_url(self, obj):
        return _resolve_media_or_external_url(self.context.get("request"), obj.image, None)


class ProductListSerializer(serializers.ModelSerializer):
    category = ProductCategoryInlineSerializer(read_only=True)
    brand = BrandInlineSerializer(read_only=True)
    variants = ProductVariantInlineSerializer(many=True, read_only=True)
    attribute_values = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "price", "promo_price", "effective_price",
            "currency", "has_variants", "product_type", "variants", "images",
            "primary_image",
            "attribute_values",
            "category", "brand", "created_at",
        ]
        read_only_fields = fields

    def get_images(self, obj):
        return ProductImageSerializer(obj.images.all(), many=True).data

    def get_primary_image(self, obj):
        images = list(obj.images.all())
        if images:
            primary = next((image for image in images if image.is_primary), images[0])
            return _resolve_media_or_external_url(
                self.context.get("request"), primary.image, primary.image_url
            )

        for variant in obj.variants.all():
            variant_url = _resolve_media_or_external_url(
                self.context.get("request"), variant.image, None
            )
            if variant_url:
                return variant_url

        return None

    def get_attribute_values(self, obj):
        values = obj.attribute_values.all().select_related("attribute")
        result = [
            {
                "id": value.id,
                "attribute": value.attribute.name,
                "value": value.value,
            }
            for value in values
        ]
        return ProductAttributeSelectionSerializer(result, many=True).data

    def get_product_type(self, obj):
        return ProductTypeChoices.VARIABLE if obj.has_variants else ProductTypeChoices.SIMPLE


class ProductDetailSerializer(serializers.ModelSerializer):
    category = ProductCategoryInlineSerializer(read_only=True)
    brand = BrandInlineSerializer(read_only=True)
    variants = ProductVariantInlineSerializer(many=True, read_only=True)
    attribute_values = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description",
            "price", "promo_price", "effective_price",
            "currency", "has_variants", "product_type", "variants", "images",
            "primary_image",
            "attribute_values",
            "category", "brand",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_images(self, obj):
        return ProductImageSerializer(obj.images.all(), many=True).data

    def get_primary_image(self, obj):
        images = list(obj.images.all())
        if images:
            primary = next((image for image in images if image.is_primary), images[0])
            return _resolve_media_or_external_url(
                self.context.get("request"), primary.image, primary.image_url
            )

        for variant in obj.variants.all():
            variant_url = _resolve_media_or_external_url(
                self.context.get("request"), variant.image, None
            )
            if variant_url:
                return variant_url

        return None

    def get_attribute_values(self, obj):
        values = obj.attribute_values.all().select_related("attribute")
        result = [
            {
                "id": value.id,
                "attribute": value.attribute.name,
                "value": value.value,
            }
            for value in values
        ]
        return ProductAttributeSelectionSerializer(result, many=True).data

    def get_product_type(self, obj):
        return ProductTypeChoices.VARIABLE if obj.has_variants else ProductTypeChoices.SIMPLE


class ProductTypeChoices:
    SIMPLE = "SIMPLE"
    VARIABLE = "VARIABLE"
    CHOICES = (
        (SIMPLE, "Simple Product"),
        (VARIABLE, "Variable Product"),
    )


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "alt_text", "is_primary", "ordering"]
        read_only_fields = ["id"]

    def get_image_url(self, obj):
        return _resolve_media_or_external_url(
            self.context.get("request"), obj.image, obj.image_url
        )


class ProductImageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "alt_text", "is_primary", "ordering"]
        read_only_fields = ["id"]


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
    product_type = serializers.ChoiceField(
        choices=ProductTypeChoices.CHOICES,
        required=False,
        write_only=True,
    )
    attribute_value_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        write_only=True,
    )
    images = ProductImageWriteSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "description",
            "price", "promo_price",
            "currency", "category", "brand",
            "is_active", "is_visible", "has_variants", "product_type", "attribute_value_ids", "images",
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

    def validate_images(self, value):
        primary_count = sum(1 for row in value if row.get("is_primary"))
        if primary_count > 1:
            raise serializers.ValidationError("Only one image can be marked as primary.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        product_type = attrs.pop("product_type", None)
        if product_type is not None:
            mapped_has_variants = product_type == ProductTypeChoices.VARIABLE
            has_variants = attrs.get("has_variants")
            if has_variants is not None and has_variants != mapped_has_variants:
                raise serializers.ValidationError(
                    {
                        "product_type": (
                            "product_type conflicts with has_variants. "
                            "Use either product_type or has_variants with matching values."
                        )
                    }
                )
            attrs["has_variants"] = mapped_has_variants

        raw_ids = attrs.pop("attribute_value_ids", None)
        if raw_ids is not None:
            deduped_ids = list(dict.fromkeys(raw_ids))
            values_qs = ProductAttributeValue.objects.filter(pk__in=deduped_ids).select_related("attribute")
            values = list(values_qs)
            if len(values) != len(deduped_ids):
                raise serializers.ValidationError(
                    {"attribute_value_ids": "One or more attribute values do not exist."}
                )

            seen_attributes = set()
            for attr_value in values:
                if attr_value.attribute_id in seen_attributes:
                    raise serializers.ValidationError(
                        {
                            "attribute_value_ids": (
                                "Product cannot contain two values from the same attribute."
                            )
                        }
                    )
                seen_attributes.add(attr_value.attribute_id)

            attrs["attribute_values"] = values

        return attrs

    def _create_images(self, product: Product, images_data: list[dict]) -> None:
        if not images_data:
            return

        if any(row.get("is_primary") for row in images_data):
            ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)

        ProductImage.objects.bulk_create(
            [ProductImage(product=product, **row) for row in images_data]
        )

    def create(self, validated_data):
        attribute_values = validated_data.pop("attribute_values", [])
        images_data = validated_data.pop("images", [])
        with transaction.atomic():
            product = super().create(validated_data)
            if attribute_values:
                product.attribute_values.set(attribute_values)
            self._create_images(product, images_data)
        return product

    def update(self, instance, validated_data):
        attribute_values = validated_data.pop("attribute_values", None)
        images_data = validated_data.pop("images", None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if attribute_values is not None:
                instance.attribute_values.set(attribute_values)
            if images_data is not None:
                self._create_images(instance, images_data)
        return instance


class BrandSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
            "image_url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "image_url", "created_at", "updated_at"]

    def get_image_url(self, obj):
        return _resolve_media_or_external_url(self.context.get("request"), obj.image, None)


class ProductAttributeValueInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttributeValue
        fields = ["id", "value"]
        read_only_fields = fields


class ProductAttributeSelectionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    attribute = serializers.CharField(read_only=True)
    value = serializers.CharField(read_only=True)


class ProductAttributeSerializer(serializers.ModelSerializer):
    values = ProductAttributeValueInlineSerializer(many=True, read_only=True)

    class Meta:
        model = ProductAttribute
        fields = ["id", "name", "values"]
        read_only_fields = ["id", "values"]


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    attribute = serializers.PrimaryKeyRelatedField(read_only=True)
    attribute_name = serializers.CharField(source="attribute.name", read_only=True)

    class Meta:
        model = ProductAttributeValue
        fields = ["id", "attribute", "attribute_name", "value"]
        read_only_fields = ["id", "attribute", "attribute_name"]


class ProductAttributeValueWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttributeValue
        fields = ["id", "value"]
        read_only_fields = ["id"]


class ProductVariantAttributeValueSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    attribute = serializers.CharField(read_only=True)
    value = serializers.CharField(read_only=True)


class ProductVariantSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    attribute_values = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "stock",
            "price_override",
            "promo_price",
            "effective_price",
            "image_url",
            "is_active",
            "attribute_values",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_attribute_values(self, obj):
        links = obj.attribute_values.select_related("attribute_value__attribute")
        result = []
        for link in links:
            result.append(
                {
                    "id": link.attribute_value_id,
                    "attribute": link.attribute_value.attribute.name,
                    "value": link.attribute_value.value,
                }
            )
        return ProductVariantAttributeValueSerializer(result, many=True).data

    def get_image_url(self, obj):
        return _resolve_media_or_external_url(self.context.get("request"), obj.image, None)


class ProductVariantWriteSerializer(serializers.ModelSerializer):
    attribute_value_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "stock",
            "price_override",
            "promo_price",
            "is_active",
            "attribute_value_ids",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        product: Product = self.context["product"]
        sku = attrs.get("sku")
        if sku:
            sku_qs = ProductVariant.objects.filter(product=product, sku=sku)
            if self.instance is not None:
                sku_qs = sku_qs.exclude(pk=self.instance.pk)
            if sku_qs.exists():
                raise serializers.ValidationError(
                    {"sku": "Variant with this SKU already exists for this product."}
                )

        raw_ids = attrs.pop("attribute_value_ids", None)
        if raw_ids is None:
            return attrs

        deduped_ids = list(dict.fromkeys(raw_ids))
        values_qs = ProductAttributeValue.objects.filter(pk__in=deduped_ids).select_related("attribute")
        values = list(values_qs)
        if len(values) != len(deduped_ids):
            raise serializers.ValidationError(
                {"attribute_value_ids": "One or more attribute values do not exist."}
            )

        seen_attributes = set()
        for attr_value in values:
            if attr_value.attribute_id in seen_attributes:
                raise serializers.ValidationError(
                    {
                        "attribute_value_ids": (
                            "A variant cannot contain two values from the same attribute."
                        )
                    }
                )
            seen_attributes.add(attr_value.attribute_id)

        attrs["attribute_values"] = values
        return attrs

    def _set_variant_attribute_values(
        self,
        variant: ProductVariant,
        attribute_values: list[ProductAttributeValue],
    ) -> None:
        ProductVariantAttributeValue.objects.filter(variant=variant).delete()
        if attribute_values:
            ProductVariantAttributeValue.objects.bulk_create(
                [
                    ProductVariantAttributeValue(variant=variant, attribute_value=value)
                    for value in attribute_values
                ]
            )

    def create(self, validated_data):
        product: Product = self.context["product"]
        attribute_values = validated_data.pop("attribute_values", [])
        validated_data["attributes_hash"] = _compute_attribute_hash(
            [value.pk for value in attribute_values]
        )

        try:
            with transaction.atomic():
                variant = ProductVariant.objects.create(product=product, **validated_data)
                self._set_variant_attribute_values(variant, attribute_values)
                return variant
        except IntegrityError as exc:
            if "unique_variant_sku_per_product" in str(exc):
                raise serializers.ValidationError(
                    {"sku": "Variant with this SKU already exists for this product."}
                ) from exc
            raise serializers.ValidationError(
                {"detail": "Variant with the same attribute combination already exists."}
            ) from exc

    def update(self, instance, validated_data):
        attribute_values = validated_data.pop("attribute_values", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if attribute_values is not None:
            instance.attributes_hash = _compute_attribute_hash([value.pk for value in attribute_values])

        try:
            with transaction.atomic():
                instance.save()
                if attribute_values is not None:
                    self._set_variant_attribute_values(instance, attribute_values)
                return instance
        except IntegrityError as exc:
            if "unique_variant_sku_per_product" in str(exc):
                raise serializers.ValidationError(
                    {"sku": "Variant with this SKU already exists for this product."}
                ) from exc
            raise serializers.ValidationError(
                {"detail": "Variant with the same attribute combination already exists."}
            ) from exc
