from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import F
from decimal import Decimal

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Inventory(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory"
    )
    quantity = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

class Dealer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

class Order(models.Model):

    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"
    STATUS_DELIVERED = "delivered"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_DELIVERED, "Delivered"),
    ]

    order_number = models.CharField(max_length=30, unique=True)
    dealer = models.ForeignKey(
        Dealer,
        on_delete=models.PROTECT,
        related_name="orders"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if self.pk:
            old_order = Order.objects.get(pk=self.pk)
            if old_order.status in [self.STATUS_CONFIRMED, self.STATUS_DELIVERED]:
                raise ValidationError(
                    "Confirmed or Delivered orders cannot be modified."
                )

        if not self.order_number:
            today = timezone.now().strftime("%Y%m%d")
            last_count = Order.objects.filter(
                order_number__startswith=f"ORD-{today}"
            ).count()
            self.order_number = f"ORD-{today}-{last_count + 1:04d}"

        super().save(*args, **kwargs)

    @transaction.atomic
    def confirm_order(self):
        if self.status != self.STATUS_DRAFT:
            raise ValidationError("Only draft orders can be confirmed.")

        if not self.items.exists():
            raise ValidationError("Order must contain at least one item.")

        items = self.items.select_related("product").select_for_update()
        errors = []

        for item in items:
            try:
                inventory = item.product.inventory
            except Inventory.DoesNotExist:
                errors.append(f"{item.product.name} has no inventory record.")
                continue

            if item.quantity > inventory.quantity:
                errors.append(
                    f"{item.product.name}: Available {inventory.quantity}, Requested {item.quantity}"
                )

        if errors:
            raise ValidationError({"stock_errors": errors})

        # Deduct stock
        for item in items:
            inventory = item.product.inventory
            inventory.quantity = F("quantity") - item.quantity
            inventory.save()

        self.status = self.STATUS_CONFIRMED
        super().save(update_fields=["status"])

    @transaction.atomic
    def deliver_order(self):

        if self.status != self.STATUS_CONFIRMED:
            raise ValidationError("Only confirmed orders can be delivered.")

        self.status = self.STATUS_DELIVERED
        super().save(update_fields=["status"])

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def save(self, *args, **kwargs):

        if self.order.status in [
            Order.STATUS_CONFIRMED,
            Order.STATUS_DELIVERED,
        ]:
            raise ValidationError(
                "Cannot modify items of a confirmed or delivered order."
            )

        self.line_total = Decimal(self.quantity) * self.unit_price
        super().save(*args, **kwargs)
        self.update_order_total()

    def delete(self, *args, **kwargs):

        if self.order.status in [
            Order.STATUS_CONFIRMED,
            Order.STATUS_DELIVERED,
        ]:
            raise ValidationError(
                "Cannot delete items from a confirmed or delivered order."
            )

        super().delete(*args, **kwargs)
        self.update_order_total()

    def update_order_total(self):
        total = sum(item.line_total for item in self.order.items.all())
        self.order.total_amount = total
        self.order.save(update_fields=["total_amount"])