from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bonuses.models import Bonus, BonusStatus, BonusType
from apps.delivery.models import Courier, DeliveryStatus
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.products.models import Product, ProductCategory, ProductVariant
from apps.reservations.models import ReservationStatus
from apps.withdrawals.models import Withdrawal, WithdrawalStatus

User = get_user_model()


def _items(payload):
    if isinstance(payload, dict) and "results" in payload:
        return payload["results"]
    return payload


class EndpointsSmokeTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            phone="+992900020001",
            first_name="Admin",
            last_name="User",
            password="testpass123",
        )
        self.user = User.objects.create_user(
            phone="+992900020002",
            first_name="Regular",
            last_name="User",
            password="testpass123",
            address="Dushanbe",
        )
        self.other = User.objects.create_user(
            phone="+992900020003",
            first_name="Other",
            last_name="User",
            password="testpass123",
            address="Khujand",
        )

        self.category = ProductCategory.objects.create(name="Phones", ordering=1, is_active=True)
        self.product = Product.objects.create(
            name="Phone X",
            description="Phone",
            price=Decimal("100.00"),
            currency="USD",
            category=self.category,
            has_variants=True,
            is_active=True,
            is_visible=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="PHONE-X-001",
            stock=20,
            price_override=Decimal("95.00"),
            is_active=True,
        )

        self.address = self.user.delivery_addresses.create(
            first_name="Regular",
            last_name="User",
            phone=self.user.phone,
            region="Region",
            city="City",
            street="Main street 1",
            is_default=True,
        )
        self.other_address = self.other.delivery_addresses.create(
            first_name="Other",
            last_name="User",
            phone=self.other.phone,
            region="Region",
            city="City",
            street="Main street 2",
            is_default=True,
        )

        self.order = Order.objects.create(
            user=self.user,
            status=OrderStatus.RESERVED,
            delivery_address=self.address,
            total_amount=Decimal("95.00"),
            delivery_fee=Decimal("5.00"),
            currency="USD",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=self.variant,
            product_name_snapshot=self.product.name,
            product_price_snapshot=Decimal("95.00"),
            quantity=1,
            line_total=Decimal("95.00"),
        )

    def test_token_endpoint_returns_jwt_pair(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"phone": self.user.phone, "password": "testpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_and_product_endpoints_permissions_are_logical(self):
        users_response = self.client.get(reverse("users-list"))
        self.assertEqual(users_response.status_code, status.HTTP_401_UNAUTHORIZED)

        products_response = self.client.get(reverse("products-list"))
        self.assertEqual(products_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.user)
        forbidden_users_response = self.client.get(reverse("users-list"))
        self.assertEqual(forbidden_users_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        admin_users_response = self.client.get(reverse("users-list"))
        self.assertEqual(admin_users_response.status_code, status.HTTP_200_OK)

    def test_orders_endpoints_return_order_number(self):
        self.client.force_authenticate(self.admin)

        list_response = self.client.get(reverse("orders-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        first_item = _items(list_response.data)[0]
        self.assertIn("order_number", first_item)
        self.assertTrue(first_item["order_number"].startswith("ORD-"))

        detail_response = self.client.get(reverse("orders-detail", kwargs={"id": self.order.id}))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertIn("order_number", detail_response.data)
        self.assertTrue(detail_response.data["order_number"].startswith("ORD-"))

    def test_order_lifecycle_endpoints_work_for_admin(self):
        self.client.force_authenticate(self.admin)

        confirm_response = self.client.post(
            reverse("orders-confirm", kwargs={"id": self.order.id}),
            {"note": "confirmed"},
            format="json",
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm_response.data["status"], OrderStatus.CONFIRMED)

        ship_response = self.client.post(
            reverse("orders-ship", kwargs={"id": self.order.id}),
            {"tracking_number": "TRK-001", "note": "shipped"},
            format="json",
        )
        self.assertEqual(ship_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ship_response.data["status"], OrderStatus.SHIPPED)

        deliver_response = self.client.post(
            reverse("orders-deliver", kwargs={"id": self.order.id}),
            {"note": "delivered"},
            format="json",
        )
        self.assertEqual(deliver_response.status_code, status.HTTP_200_OK)
        self.assertEqual(deliver_response.data["status"], OrderStatus.DELIVERED)

        cancel_response = self.client.post(
            reverse("orders-cancel", kwargs={"id": self.order.id}),
            {"note": "cannot cancel delivered"},
            format="json",
        )
        self.assertEqual(cancel_response.status_code, status.HTTP_409_CONFLICT)

    def test_delivery_endpoints_create_assign_and_update_status(self):
        courier = Courier.objects.create(first_name="Test", last_name="Courier", phone="+992901110001")
        self.client.force_authenticate(self.admin)

        create_response = self.client.post(
            reverse("deliveries-list"),
            {
                "order": str(self.order.id),
                "delivery_fee": "7.50",
                "courier": str(courier.id),
                "notes": "new delivery",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        delivery_id = create_response.data["id"]

        update_response = self.client.post(
            reverse("deliveries-update-status", kwargs={"id": delivery_id}),
            {
                "status": DeliveryStatus.SHIPPED,
                "tracking_number": "DLV-001",
                "notes": "on route",
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["status"], DeliveryStatus.SHIPPED)

        assign_response = self.client.post(
            reverse("deliveries-assign-courier-action", kwargs={"id": delivery_id}),
            {"courier": str(courier.id)},
            format="json",
        )
        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.user)
        list_response = self.client.get(reverse("deliveries-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_items(list_response.data)), 1)

    def test_reservation_checkout_endpoint_creates_reserved_order(self):
        self.client.force_authenticate(self.user)

        create_response = self.client.post(
            reverse("reservation-list"),
            {"variant_id": str(self.variant.id), "quantity": 1},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        reservation_id = create_response.data["id"]

        checkout_response = self.client.post(
            reverse("reservation-checkout"),
            {
                "reservation_ids": [reservation_id],
                "delivery_address_id": str(self.address.id),
                "delivery_fee": "3.00",
            },
            format="json",
        )
        self.assertEqual(checkout_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(checkout_response.data["status"], OrderStatus.RESERVED)

        converted_status = self.user.reservations.get(pk=reservation_id).status
        self.assertEqual(converted_status, ReservationStatus.CONVERTED)

    def test_withdrawal_and_bonus_endpoints_respect_visibility_and_flow(self):
        User.objects.filter(pk=self.user.pk).update(bonus_balance=Decimal("200.00"))
        self.user.refresh_from_db()

        self.client.force_authenticate(self.user)
        create_withdrawal_response = self.client.post(
            reverse("withdrawals-list"),
            {"amount": "50.00"},
            format="json",
        )
        self.assertEqual(create_withdrawal_response.status_code, status.HTTP_201_CREATED)
        withdrawal_id = create_withdrawal_response.data["id"]

        self.client.force_authenticate(self.admin)
        approve_response = self.client.post(
            reverse("withdrawals-approve", kwargs={"id": withdrawal_id}),
            {},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], WithdrawalStatus.APPROVED)

        self.assertTrue(Withdrawal.objects.filter(pk=withdrawal_id, status=WithdrawalStatus.APPROVED).exists())

        other_order = Order.objects.create(
            user=self.other,
            status=OrderStatus.DELIVERED,
            delivery_address=self.other_address,
            total_amount=Decimal("100.00"),
            delivery_fee=Decimal("0.00"),
            currency="USD",
        )
        user_order = Order.objects.create(
            user=self.user,
            status=OrderStatus.DELIVERED,
            delivery_address=self.address,
            total_amount=Decimal("120.00"),
            delivery_fee=Decimal("0.00"),
            currency="USD",
        )
        user_bonus = Bonus.objects.create(
            user=self.user,
            source_user=self.other,
            order=other_order,
            level=1,
            bonus_type=BonusType.PERSONAL,
            amount=Decimal("5.00"),
            status=BonusStatus.PENDING,
        )
        Bonus.objects.create(
            user=self.other,
            source_user=self.user,
            order=user_order,
            level=1,
            bonus_type=BonusType.PERSONAL,
            amount=Decimal("6.00"),
            status=BonusStatus.PENDING,
        )

        self.client.force_authenticate(self.user)
        user_bonuses_response = self.client.get(reverse("bonus-list"))
        self.assertEqual(user_bonuses_response.status_code, status.HTTP_200_OK)
        user_items = _items(user_bonuses_response.data)
        self.assertEqual(len(user_items), 1)
        self.assertEqual(user_items[0]["id"], str(user_bonus.id))
