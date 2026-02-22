from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r"products", ProductViewSet)
router.register(r"dealers", DealerViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"inventory", InventoryViewSet)

urlpatterns = router.urls