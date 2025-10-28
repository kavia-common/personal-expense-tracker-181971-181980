from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import health
from .viewsets import (
    CategoryViewSet,
    ExpenseViewSet,
    BudgetViewSet,
    RecurringRuleViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"expenses", ExpenseViewSet, basename="expense")
router.register(r"budgets", BudgetViewSet, basename="budget")
router.register(r"recurring-rules", RecurringRuleViewSet, basename="recurringrule")

urlpatterns = [
    path("health/", health, name="Health"),
    path("", include(router.urls)),
]
