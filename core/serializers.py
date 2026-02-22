from rest_framework import serializers
from .models import Product, Dealer, Order, OrderItem, Inventory

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ["id", "product", "quantity", "updated_at"]

class ProductSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "description",
            "price",
            "inventory",
            "created_at",
            "updated_at",
        ]

class DealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dealer
        fields = "__all__"

class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "quantity",
            "unit_price",
            "line_total",
        ]
        read_only_fields = ["unit_price", "line_total"]

class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "dealer",
            "status",
            "total_amount",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = [
            "order_number",
            "status",
            "total_amount",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product = item_data["product"]

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data["quantity"],
                unit_price=product.price,  # preserve price
            )

        return order

    def update(self, instance, validated_data):

        if instance.status != Order.STATUS_DRAFT:
            raise serializers.ValidationError(
                "Only draft orders can be updated."
            )

        items_data = validated_data.pop("items", None)

        instance.dealer = validated_data.get(
            "dealer", instance.dealer
        )
        instance.save()

        if items_data is not None:
            instance.items.all().delete()

            for item_data in items_data:
                product = item_data["product"]

                OrderItem.objects.create(
                    order=instance,
                    product=product,
                    quantity=item_data["quantity"],
                    unit_price=product.price,
                )

        return instance
    
