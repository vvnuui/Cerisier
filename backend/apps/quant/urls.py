from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .simulator.views import PortfolioViewSet

router = DefaultRouter()
router.register(r"quant/portfolios", PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path("", include(router.urls)),
]
