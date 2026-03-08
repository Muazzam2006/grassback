                                                                    
                                                                    
                                                                            
                                                                             

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0001_initial"),
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderDelivery",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("SHIPPED", "Shipped"),
                            ("DELIVERED", "Delivered"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=10,
                    ),
                ),
                (
                    "tracking_number",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        unique=True,
                        verbose_name="Tracking Number",
                    ),
                ),
                (
                    "delivery_fee",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=14,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00"))
                        ],
                        verbose_name="Delivery Fee",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="Delivery Notes")),
                (
                    "estimated_delivery_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("shipped_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "courier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deliveries",
                        to="delivery.courier",
                        verbose_name="Assigned Courier",
                    ),
                ),
                (
                    "delivery_address",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="deliveries",
                        to="delivery.deliveryaddress",
                        verbose_name="Delivery Address",
                    ),
                ),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="delivery",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Order Delivery",
                "verbose_name_plural": "Order Deliveries",
                "db_table": "delivery_order_delivery",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="orderdelivery",
            index=models.Index(
                fields=["status"], name="order_delivery_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="orderdelivery",
            index=models.Index(
                fields=["courier", "status"], name="ord_dlv_courier_status_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="orderdelivery",
            constraint=models.CheckConstraint(
                condition=models.Q(delivery_fee__gte=0),
                name="order_delivery_fee_gte_0",
            ),
        ),
    ]
