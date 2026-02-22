from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.core.exceptions import ValidationError
from .models import Product, Dealer, Order, Inventory
from .serializers import (
    ProductSerializer,
    DealerSerializer,
    OrderSerializer,
    InventorySerializer,
)
# Create your views here.

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class DealerViewSet(ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer

class OrderViewSet(ModelViewSet):
    queryset = Order.objects.prefetch_related("items__product")
    serializer_class = OrderSerializer

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()

        try:
            order.confirm_order()
            return Response(
                {"message": "Order confirmed successfully"},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        order = self.get_object()

        try:
            order.deliver_order()
            return Response(
                {"message": "Order delivered successfully"},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

class InventoryViewSet(ModelViewSet):
    queryset = Inventory.objects.select_related("product")
    serializer_class = InventorySerializer