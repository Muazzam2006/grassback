from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bonuses.models import Bonus, BonusStatus, BonusType, MLMRule
from apps.bonuses.services import distribute_order_bonuses
from apps.orders.models import Order, OrderStatus
from apps.products.models import Product

from .models import OTPPurpose, OTPToken, User, UserStatus



def _make_user(phone: str, sponsor: User | None = None, **kw) -> User:
    return User.objects.create_user(
        phone=phone,
        password="TestPass123!",
        first_name=kw.get("first_name", "First"),
        last_name=kw.get("last_name", "Last"),
        status=kw.get("status", UserStatus.NEW),
        parent=sponsor,
    )


def _make_rule(status: str, level: int, percent: Decimal) -> MLMRule:
    return MLMRule.objects.create(
        agent_status=status,
        level=level,
        percent=percent,
        is_active=True,
    )


def _make_product(price: Decimal = Decimal("100.00")) -> "Product":
    from apps.products.models import Product
    return Product.objects.create(
        name="Test Product",
        price=price,
        is_active=True,
    )


def _make_paid_order(buyer: User, amount: Decimal = Decimal("100.00")) -> Order:
    from apps.delivery.models import DeliveryAddress

    address = DeliveryAddress.objects.create(
        user=buyer,
        first_name=buyer.first_name,
        last_name=buyer.last_name,
        phone=buyer.phone,
        region="Test Region",
        city="Test City",
        street="Test Street 1",
    )

    order = Order.objects.create(
        user=buyer,
        total_amount=amount,
        delivery_address=address,
        currency="USD",
    )
                                                
    Order.objects.filter(pk=order.pk).update(status=OrderStatus.DELIVERED)
    return Order.objects.get(pk=order.pk)

class UserStatusTest(TestCase):
    def test_choices(self):
        values = {c[0] for c in UserStatus.choices}
        self.assertEqual(values, {"NEW", "BRONZE", "SILVER", "GOLD"})


class UserTreeTest(TestCase):

    def setUp(self):
        self.root = _make_user("+10000000001")
        self.child = _make_user("+10000000002", sponsor=self.root)
        self.grandchild = _make_user("+10000000003", sponsor=self.child)
                                                   
        self.root.refresh_from_db()
        self.child.refresh_from_db()
        self.grandchild.refresh_from_db()

    def test_root_level_is_zero(self):
        self.assertEqual(self.root.level, 0)

    def test_child_level_is_one(self):
        self.assertEqual(self.child.level, 1)

    def test_grandchild_level_is_two(self):
        self.assertEqual(self.grandchild.level, 2)

    def test_lft_rght_bounds(self):
                                                                        
        self.assertLess(self.root.lft, self.child.lft)
        self.assertGreater(self.root.rght, self.child.rght)
        self.assertLess(self.child.lft, self.grandchild.lft)
        self.assertGreater(self.child.rght, self.grandchild.rght)

    def test_same_tree_id(self):
        self.assertEqual(self.root.tree_id, self.child.tree_id)
        self.assertEqual(self.root.tree_id, self.grandchild.tree_id)


class SponsorAliasTest(TestCase):
    def setUp(self):
        self.root = _make_user("+10000000010")
        self.child = _make_user("+10000000011", sponsor=self.root)

    def test_sponsor_property_returns_parent(self):
        self.child.refresh_from_db()
        self.assertEqual(self.child.sponsor, self.root)

    def test_sponsor_id_property(self):
        self.child.refresh_from_db()
        self.assertEqual(self.child.sponsor_id, self.root.pk)

    def test_sponsor_none_for_root(self):
        self.assertIsNone(self.root.sponsor)


class AncestorDescendantTest(TestCase):
    def setUp(self):
        self.l0 = _make_user("+10000000020")
        self.l1 = _make_user("+10000000021", sponsor=self.l0)
        self.l2 = _make_user("+10000000022", sponsor=self.l1)
        self.l3 = _make_user("+10000000023", sponsor=self.l2)

    def test_get_ancestors_ascending_order(self):
        """Nearest sponsor first (ascending=True)."""
        ancestors = list(
            self.l3.get_ancestors(ascending=True).values_list("pk", flat=True)
        )
        self.assertEqual(ancestors, [self.l2.pk, self.l1.pk, self.l0.pk])

    def test_get_descendants(self):
        descendants = set(
            self.l0.get_descendants().values_list("pk", flat=True)
        )
        self.assertEqual(descendants, {self.l1.pk, self.l2.pk, self.l3.pk})

    def test_is_ancestor_of(self):
        self.assertTrue(self.l0.is_ancestor_of(self.l3))
        self.assertFalse(self.l3.is_ancestor_of(self.l0))

    def test_is_descendant_of(self):
        self.assertTrue(self.l3.is_descendant_of(self.l0))
        self.assertFalse(self.l0.is_descendant_of(self.l3))


class CircularReferenceTest(TestCase):
    def test_self_sponsor_raises_validation_error(self):
        user = _make_user("+10000000030")
        user.parent = user
        with self.assertRaises(ValidationError):
            user.clean()

    def test_descendant_as_parent_raises_validation_error(self):
        root = _make_user("+10000000031")
        child = _make_user("+10000000032", sponsor=root)
                                                        
        root.parent = child
        with self.assertRaises(ValidationError):
            root.clean()


class BonusDistributionTest(TestCase):

    def setUp(self):
        self.gold_root = _make_user("+10000000040", status=UserStatus.GOLD)
        self.silver_mid = _make_user(
            "+10000000041", sponsor=self.gold_root, status=UserStatus.SILVER
        )
        self.buyer = _make_user("+10000000042", sponsor=self.silver_mid)

                                          
        _make_rule("SILVER", 1, Decimal("5.00"))
                                                   
        _make_rule("GOLD", 2, Decimal("3.00"))

        self.order = _make_paid_order(self.buyer, Decimal("200.00"))

    def test_creates_two_bonuses(self):
        bonuses = distribute_order_bonuses(self.order)
        self.assertEqual(len(bonuses), 2)

    def test_l1_bonus_to_silver_mid(self):
        distribute_order_bonuses(self.order)
        b = Bonus.objects.get(user=self.silver_mid, level=1, bonus_type=BonusType.PERSONAL)
                           
        self.assertEqual(b.amount, Decimal("10.00"))
        self.assertEqual(b.status, BonusStatus.PENDING)
        self.assertEqual(b.source_user, self.buyer)

    def test_l2_bonus_to_gold_root(self):
        distribute_order_bonuses(self.order)
        b = Bonus.objects.get(user=self.gold_root, level=2, bonus_type=BonusType.TEAM)
                          
        self.assertEqual(b.amount, Decimal("6.00"))

    def test_no_bonus_for_buyer(self):
        distribute_order_bonuses(self.order)
        self.assertFalse(Bonus.objects.filter(user=self.buyer).exists())


class BonusIdempotencyTest(TestCase):
    def setUp(self):
        self.sponsor = _make_user("+10000000050", status=UserStatus.SILVER)
        self.buyer = _make_user("+10000000051", sponsor=self.sponsor)
        _make_rule("SILVER", 1, Decimal("10.00"))
        self.order = _make_paid_order(self.buyer, Decimal("100.00"))

    def test_retry_does_not_create_duplicates(self):
        first_run = distribute_order_bonuses(self.order)
        second_run = distribute_order_bonuses(self.order)
        self.assertEqual(len(first_run), 1)
        self.assertEqual(len(second_run), 0)                               
        self.assertEqual(Bonus.objects.filter(order=self.order).count(), 1)


class TreeRebuildTest(TransactionTestCase):

    def test_rebuild_restores_lft_rght(self):
        root = _make_user("+10000000060")
        child = _make_user("+10000000061", sponsor=root)
        grandchild = _make_user("+10000000062", sponsor=child)

                                                                     
        User.objects.filter(pk__in=[root.pk, child.pk, grandchild.pk]).update(
            lft=0, rght=0, tree_id=0, level=0
        )

                                                       
        User.objects.rebuild()

        root.refresh_from_db()
        child.refresh_from_db()
        grandchild.refresh_from_db()

        self.assertEqual(root.level, 0)
        self.assertEqual(child.level, 1)
        self.assertEqual(grandchild.level, 2)
        self.assertLess(root.lft, child.lft)
        self.assertGreater(root.rght, child.rght)


class UserRegistrationOTPApiTests(APITestCase):
    def test_request_registration_otp_creates_token(self):
        with patch("apps.users.services.send_oson_sms") as mocked_send_sms:
            response = self.client.post(
                reverse("users-request-registration-otp"),
                {"phone": "+992900010001"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "OTP code sent successfully.")
        self.assertTrue(
            OTPToken.objects.filter(phone="+992900010001", purpose=OTPPurpose.REGISTER, is_used=False).exists()
        )
        mocked_send_sms.assert_called_once()

    def test_verify_otp_then_create_user_without_password(self):
        raw_code = "123456"
        OTPToken.objects.create(
            phone="+992900010002",
            code_hash=OTPToken.hash_code(raw_code),
            purpose=OTPPurpose.REGISTER,
            is_used=False,
            attempts=0,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        verify_response = self.client.post(
            reverse("users-verify-registration-otp"),
            {
                "phone": "+992900010002",
                "otp_code": raw_code,
            },
            format="json",
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            reverse("users-list"),
            {
                "phone": "+992900010002",
                "first_name": "Otp",
                "last_name": "User",
                "address": "Dushanbe, Rudaki 1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(phone="+992900010002")
        self.assertEqual(user.address, "Dushanbe, Rudaki 1")
        self.assertFalse(user.has_usable_password())
        self.assertFalse(OTPToken.objects.filter(phone="+992900010002", purpose=OTPPurpose.REGISTER, is_used=False).exists())

    def test_create_user_without_verified_phone_rejected(self):
        response = self.client.post(
            reverse("users-list"),
            {
                "phone": "+992900010003",
                "first_name": "No",
                "last_name": "Otp",
                "address": "Dushanbe",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Phone number is not verified. Verify OTP code first.", response.data["phone"])

    def test_create_user_without_address_rejected(self):
        raw_code = "123456"
        OTPToken.objects.create(
            phone="+992900010004",
            code_hash=OTPToken.hash_code(raw_code),
            purpose=OTPPurpose.REGISTER,
            is_used=False,
            attempts=0,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.client.post(
            reverse("users-verify-registration-otp"),
            {
                "phone": "+992900010004",
                "otp_code": raw_code,
            },
            format="json",
        )

        response = self.client.post(
            reverse("users-list"),
            {
                "phone": "+992900010004",
                "first_name": "Missing",
                "last_name": "Address",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("address", response.data)
