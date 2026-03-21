from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Brand,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductCategory,
    ProductImage,
    ProductVariant,
)

User = get_user_model()


def _items(payload):
    if isinstance(payload, dict) and "results" in payload:
        return payload["results"]
    return payload


class ProductTypeApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            phone="+992900000001",
            first_name="Admin",
            last_name="User",
            password="testpass123",
        )
        self.client.force_authenticate(self.admin)
        self.category = ProductCategory.objects.create(name="Phones", ordering=1, is_active=True)
        self.color_attribute = ProductAttribute.objects.create(name="Color")
        self.size_attribute = ProductAttribute.objects.create(name="Size")
        self.color_black = ProductAttributeValue.objects.create(attribute=self.color_attribute, value="Black")
        self.color_white = ProductAttributeValue.objects.create(attribute=self.color_attribute, value="White")
        self.size_m = ProductAttributeValue.objects.create(attribute=self.size_attribute, value="M")

    def test_create_simple_product_by_product_type(self):
        payload = {
            "name": "Simple Product",
            "description": "Simple",
            "price": "100.00",
            "currency": "usd",
            "category": str(self.category.id),
            "product_type": "SIMPLE",
        }

        response = self.client.post(reverse("products-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.data["id"])
        self.assertFalse(product.has_variants)

    def test_create_variable_product_by_product_type(self):
        payload = {
            "name": "Variable Product",
            "description": "Variable",
            "price": "250.00",
            "currency": "USD",
            "category": str(self.category.id),
            "product_type": "VARIABLE",
        }

        response = self.client.post(reverse("products-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.data["id"])
        self.assertTrue(product.has_variants)

    def test_create_product_with_multiple_characteristics(self):
        payload = {
            "name": "Simple Product With Attributes",
            "description": "Simple",
            "price": "100.00",
            "currency": "TJS",
            "category": str(self.category.id),
            "product_type": "SIMPLE",
            "attribute_value_ids": [str(self.color_black.id), str(self.size_m.id)],
        }

        response = self.client.post(reverse("products-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.data["id"])
        selected_ids = set(product.attribute_values.values_list("id", flat=True))
        self.assertEqual(selected_ids, {self.color_black.id, self.size_m.id})

    def test_create_product_rejects_two_values_from_same_attribute(self):
        payload = {
            "name": "Simple Product Invalid Attributes",
            "description": "Simple",
            "price": "100.00",
            "currency": "TJS",
            "category": str(self.category.id),
            "product_type": "SIMPLE",
            "attribute_value_ids": [str(self.color_black.id), str(self.color_white.id)],
        }

        response = self.client.post(reverse("products-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("attribute_value_ids", response.data)


class NestedProductsApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            phone="+992900000002",
            first_name="Admin",
            last_name="User",
            password="testpass123",
        )

        self.category = ProductCategory.objects.create(name="Laptops", ordering=1, is_active=True)
        self.product = Product.objects.create(
            name="Laptop",
            description="Laptop description",
            price="1200.00",
            currency="USD",
            category=self.category,
            has_variants=True,
            is_active=True,
            is_visible=True,
        )
        self.product_two = Product.objects.create(
            name="Laptop Pro",
            description="Laptop pro description",
            price="1800.00",
            currency="USD",
            category=self.category,
            has_variants=True,
            is_active=True,
            is_visible=True,
        )
        self.attribute = ProductAttribute.objects.create(name="Color")
        self.attribute_value = ProductAttributeValue.objects.create(
            attribute=self.attribute,
            value="Black",
        )

    def test_attribute_values_nested_endpoints(self):
        self.client.force_authenticate(self.admin)
        create_response = self.client.post(
            reverse("attribute-values-list", kwargs={"attribute_id": self.attribute.id}),
            {"value": "White"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(
            reverse("attribute-values-list", kwargs={"attribute_id": self.attribute.id})
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(_items(list_response.data)), 2)

    def test_categories_list_contains_image_url_field(self):
        response = self.client.get(reverse("categories-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        categories = _items(response.data)
        target = next(item for item in categories if item["id"] == str(self.category.id))
        self.assertIn("image_url", target)
        self.assertIsNone(target["image_url"])

    def test_categories_list_returns_uploaded_image_url(self):
        category_with_image = ProductCategory.objects.create(
            name="With Image",
            ordering=2,
            is_active=True,
            image="categories/with-image.png",
        )

        response = self.client.get(reverse("categories-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        categories = _items(response.data)
        target = next(item for item in categories if item["id"] == str(category_with_image.id))
        self.assertTrue(target["image_url"])
        self.assertTrue(target["image_url"].endswith("/media/categories/with-image.png"))

    def test_brands_list_contains_image_url_field(self):
        brand = Brand.objects.create(name="Flow Brand", is_active=True)

        response = self.client.get(reverse("brands-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        brands = _items(response.data)
        target = next(item for item in brands if item["id"] == str(brand.id))
        self.assertIn("image_url", target)
        self.assertIsNone(target["image_url"])

    def test_brands_list_returns_uploaded_image_url(self):
        brand = Brand.objects.create(
            name="Flow Brand With Image",
            is_active=True,
            image="brands/flow-brand.png",
        )

        response = self.client.get(reverse("brands-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        brands = _items(response.data)
        target = next(item for item in brands if item["id"] == str(brand.id))
        self.assertTrue(target["image_url"])
        self.assertTrue(target["image_url"].endswith("/media/brands/flow-brand.png"))

    def test_product_variants_nested_endpoints(self):
        self.client.force_authenticate(self.admin)

        create_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "LAPTOP-BLK-001",
                "stock": 10,
                "price_override": "1100.00",
                "attribute_value_ids": [str(self.attribute_value.id)],
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug})
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_items(list_response.data)), 1)

    def test_product_variants_allow_multiple_without_attributes(self):
        self.client.force_authenticate(self.admin)

        first_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "LAPTOP-EMPTY-001",
                "stock": 5,
                "price_override": "1150.00",
                "attribute_value_ids": [],
            },
            format="json",
        )
        second_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "LAPTOP-EMPTY-002",
                "stock": 3,
                "price_override": "1125.00",
                "attribute_value_ids": [],
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)

    def test_product_variants_duplicate_attribute_combination_rejected(self):
        self.client.force_authenticate(self.admin)

        first_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "LAPTOP-BLK-010",
                "stock": 8,
                "price_override": "1110.00",
                "attribute_value_ids": [str(self.attribute_value.id)],
            },
            format="json",
        )
        second_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "LAPTOP-BLK-011",
                "stock": 2,
                "price_override": "1115.00",
                "attribute_value_ids": [str(self.attribute_value.id)],
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_product_variants_same_sku_allowed_for_different_products(self):
        self.client.force_authenticate(self.admin)

        first_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "SKU-SHARED-001",
                "stock": 8,
                "price_override": "1110.00",
                "attribute_value_ids": [str(self.attribute_value.id)],
            },
            format="json",
        )
        second_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product_two.slug}),
            {
                "sku": "SKU-SHARED-001",
                "stock": 2,
                "price_override": "1715.00",
                "attribute_value_ids": [],
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)

    def test_product_variants_duplicate_sku_rejected_within_same_product(self):
        self.client.force_authenticate(self.admin)

        first_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "SKU-SAME-PRODUCT-001",
                "stock": 8,
                "price_override": "1110.00",
                "attribute_value_ids": [str(self.attribute_value.id)],
            },
            format="json",
        )
        second_response = self.client.post(
            reverse("product-variants-list", kwargs={"product_slug": self.product.slug}),
            {
                "sku": "SKU-SAME-PRODUCT-001",
                "stock": 2,
                "price_override": "1115.00",
                "attribute_value_ids": [],
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sku", second_response.data)

    def test_product_images_nested_endpoints(self):
        self.client.force_authenticate(self.admin)

        create_response = self.client.post(
            reverse("product-images-list", kwargs={"product_slug": self.product.slug}),
            {
                "image_url": "https://example.com/laptop.jpg",
                "alt_text": "Laptop image",
                "is_primary": True,
                "ordering": 1,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(
            reverse("product-images-list", kwargs={"product_slug": self.product.slug})
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_items(list_response.data)), 1)

    def test_product_detail_returns_selected_characteristics(self):
        size_attribute = ProductAttribute.objects.create(name="Size")
        size_value = ProductAttributeValue.objects.create(attribute=size_attribute, value="15-inch")
        self.product.attribute_values.add(self.attribute_value, size_value)

        response = self.client.get(reverse("products-detail", kwargs={"slug": self.product.slug}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attributes = response.data.get("attribute_values", [])
        labels = {(item["attribute"], item["value"]) for item in attributes}
        self.assertIn(("Color", "Black"), labels)
        self.assertIn(("Size", "15-inch"), labels)

    def test_products_list_returns_variant_image_and_primary_image_fallback(self):
        ProductVariant.objects.create(
            product=self.product,
            sku="LAPTOP-IMG-001",
            stock=4,
            price_override="1190.00",
            is_active=True,
            attributes_hash="",
            image="products/variants/laptop-black.png",
        )

        response = self.client.get(reverse("products-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        products = _items(response.data)
        target = next(item for item in products if item["id"] == str(self.product.id))

        self.assertTrue(target["primary_image"])
        self.assertTrue(target["primary_image"].endswith("/media/products/variants/laptop-black.png"))
        self.assertGreaterEqual(len(target["variants"]), 1)
        first_variant = target["variants"][0]
        self.assertIn("image_url", first_variant)
        self.assertTrue(first_variant["image_url"])
        self.assertTrue(first_variant["image_url"].endswith("/media/products/variants/laptop-black.png"))

    def test_products_list_brand_contains_image_url(self):
        brand = Brand.objects.create(
            name="Flow Product Brand",
            is_active=True,
            image="brands/flow-product-brand.png",
        )
        self.product.brand = brand
        self.product.save(update_fields=["brand"])

        response = self.client.get(reverse("products-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        products = _items(response.data)
        target = next(item for item in products if item["id"] == str(self.product.id))
        self.assertEqual(target["brand"]["id"], str(brand.id))
        self.assertIn("image_url", target["brand"])
        self.assertTrue(target["brand"]["image_url"])
        self.assertTrue(
            target["brand"]["image_url"].endswith("/media/brands/flow-product-brand.png")
        )

    def test_product_detail_images_use_uploaded_file_url(self):
        ProductImage.objects.create(
            product=self.product,
            image="products/images/laptop-main.png",
            alt_text="main",
            is_primary=True,
            ordering=1,
        )

        response = self.client.get(reverse("products-detail", kwargs={"slug": self.product.slug}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["images"]), 1)
        image_url = response.data["images"][0]["image_url"]
        self.assertTrue(image_url)
        self.assertTrue(image_url.endswith("/media/products/images/laptop-main.png"))
        self.assertTrue(response.data["primary_image"].endswith("/media/products/images/laptop-main.png"))
