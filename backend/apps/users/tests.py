"""
Production-grade tests for users app MPTT integration.

Test areas:
  1. UserStatus choices integrity
  2. User tree construction — lft/rght/level correctness
  3. sponsor property alias backward-compat
  4. Ancestor/descendant MPTT queries
  5. Circular reference validation
  6. Bonus distribution via get_ancestors (no Python iteration)
  7. Idempotency of distribute_order_bonuses
  8. Tree integrity after rebuild
"""
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase

from apps.bonuses.models import Bonus, BonusStatus, BonusType, MLMRule
from apps.bonuses.services import distribute_order_bonuses
from apps.orders.models import Order, OrderStatus
from apps.products.models import Product

from .models import User, UserStatus



def _make_user(phone: str, sponsor: User | None = None, **kw) -> User:
    """Create a user without going through the REST API."""
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
    # COD flow: financial validity is DELIVERED.
    Order.objects.filter(pk=order.pk).update(status=OrderStatus.DELIVERED)
    return Order.objects.get(pk=order.pk)


# ---------------------------------------------------------------------------
# 1. Model field tests
# ---------------------------------------------------------------------------

class UserStatusTest(TestCase):
    def test_choices(self):
        values = {c[0] for c in UserStatus.choices}
        self.assertEqual(values, {"NEW", "BRONZE", "SILVER", "GOLD"})


# ---------------------------------------------------------------------------
# 2. MPTT tree construction
# ---------------------------------------------------------------------------

class UserTreeTest(TestCase):
    """Verify that MPTT fields are populated correctly after save."""

    def setUp(self):
        self.root = _make_user("+10000000001")
        self.child = _make_user("+10000000002", sponsor=self.root)
        self.grandchild = _make_user("+10000000003", sponsor=self.child)
        # Refresh from DB to get fresh MPTT fields.
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
        # Root must fully envelope child which must envelope grandchild.
        self.assertLess(self.root.lft, self.child.lft)
        self.assertGreater(self.root.rght, self.child.rght)
        self.assertLess(self.child.lft, self.grandchild.lft)
        self.assertGreater(self.child.rght, self.grandchild.rght)

    def test_same_tree_id(self):
        self.assertEqual(self.root.tree_id, self.child.tree_id)
        self.assertEqual(self.root.tree_id, self.grandchild.tree_id)


# ---------------------------------------------------------------------------
# 3. Backward-compat sponsor alias
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 4. MPTT ancestor / descendant queries
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 5. Circular reference validation
# ---------------------------------------------------------------------------

class CircularReferenceTest(TestCase):
    def test_self_sponsor_raises_validation_error(self):
        user = _make_user("+10000000030")
        user.parent = user
        with self.assertRaises(ValidationError):
            user.clean()

    def test_descendant_as_parent_raises_validation_error(self):
        root = _make_user("+10000000031")
        child = _make_user("+10000000032", sponsor=root)
        # Attempt to make root's parent = child (cycle).
        root.parent = child
        with self.assertRaises(ValidationError):
            root.clean()


# ---------------------------------------------------------------------------
# 6. Bonus distribution via MPTT ancestors
# ---------------------------------------------------------------------------

class BonusDistributionTest(TestCase):
    """
    3-level tree: gold_root → silver_mid → buyer
    MLM rules produce bonuses at L1 (PERSONAL) and L2 (TEAM).
    """

    def setUp(self):
        self.gold_root = _make_user("+10000000040", status=UserStatus.GOLD)
        self.silver_mid = _make_user(
            "+10000000041", sponsor=self.gold_root, status=UserStatus.SILVER
        )
        self.buyer = _make_user("+10000000042", sponsor=self.silver_mid)

        # L1 rule: SILVER sponsors get 5 %
        _make_rule("SILVER", 1, Decimal("5.00"))
        # L2 rule: GOLD sponsors get 3 % at level 2
        _make_rule("GOLD", 2, Decimal("3.00"))

        self.order = _make_paid_order(self.buyer, Decimal("200.00"))

    def test_creates_two_bonuses(self):
        bonuses = distribute_order_bonuses(self.order)
        self.assertEqual(len(bonuses), 2)

    def test_l1_bonus_to_silver_mid(self):
        distribute_order_bonuses(self.order)
        b = Bonus.objects.get(user=self.silver_mid, level=1, bonus_type=BonusType.PERSONAL)
        # 5% of 200 = 10.00
        self.assertEqual(b.amount, Decimal("10.00"))
        self.assertEqual(b.status, BonusStatus.PENDING)
        self.assertEqual(b.source_user, self.buyer)

    def test_l2_bonus_to_gold_root(self):
        distribute_order_bonuses(self.order)
        b = Bonus.objects.get(user=self.gold_root, level=2, bonus_type=BonusType.TEAM)
        # 3% of 200 = 6.00
        self.assertEqual(b.amount, Decimal("6.00"))

    def test_no_bonus_for_buyer(self):
        distribute_order_bonuses(self.order)
        self.assertFalse(Bonus.objects.filter(user=self.buyer).exists())


# ---------------------------------------------------------------------------
# 7. Idempotency
# ---------------------------------------------------------------------------

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
        self.assertEqual(len(second_run), 0)  # idempotent — no new records
        self.assertEqual(Bonus.objects.filter(order=self.order).count(), 1)


# ---------------------------------------------------------------------------
# 8. Tree rebuild integrity
# ---------------------------------------------------------------------------

class TreeRebuildTest(TransactionTestCase):
    """
    TransactionTestCase required because rebuild() uses raw DB-level ops
    that may not play nicely inside a wrapped test transaction.
    """

    def test_rebuild_restores_lft_rght(self):
        root = _make_user("+10000000060")
        child = _make_user("+10000000061", sponsor=root)
        grandchild = _make_user("+10000000062", sponsor=child)

        # Corrupt lft/rght directly to simulate a stale import state.
        User.objects.filter(pk__in=[root.pk, child.pk, grandchild.pk]).update(
            lft=0, rght=0, tree_id=0, level=0
        )

        # Rebuild must restore valid nested-set values.
        User.objects.rebuild()

        root.refresh_from_db()
        child.refresh_from_db()
        grandchild.refresh_from_db()

        self.assertEqual(root.level, 0)
        self.assertEqual(child.level, 1)
        self.assertEqual(grandchild.level, 2)
        self.assertLess(root.lft, child.lft)
        self.assertGreater(root.rght, child.rght)
