from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Product, ProductAttribute, ProductAttributeValue, ProductCategory

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
