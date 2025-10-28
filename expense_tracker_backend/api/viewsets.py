from django.db.models import QuerySet
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated

from .models import Category, Expense, Budget, RecurringRule
from .permissions import IsOwner
from .serializers import (
    CategorySerializer,
    ExpenseSerializer,
    BudgetSerializer,
    RecurringRuleSerializer,
)


class OwnedQuerysetMixin:
    """
    Mixin to scope queryset to request.user and inject request into serializer context.
    """

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()  # type: ignore
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            return qs.filter(user=user)
        # No unauthenticated access
        return qs.none()

    def get_serializer_context(self) -> dict:
        ctx = super().get_serializer_context()
        ctx["request"] = getattr(self, "request", None)
        return ctx


# PUBLIC_INTERFACE
class CategoryViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """CRUD for user-owned categories."""
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Category.objects.all()


# PUBLIC_INTERFACE
class ExpenseViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """CRUD for user-owned expenses with basic filtering by date range and category.

    Supported query params:
    - start_date=YYYY-MM-DD
    - end_date=YYYY-MM-DD
    - category=<category_id>
    """
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Expense.objects.select_related("category", "recurring_rule").all()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "created_at", "amount"]
    ordering = ["-date", "-created_at"]

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()

        # Basic filtering
        start = self.request.query_params.get("start_date")
        end = self.request.query_params.get("end_date")
        category = self.request.query_params.get("category")

        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        if category:
            qs = qs.filter(category_id=category)

        return qs


# PUBLIC_INTERFACE
class BudgetViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """CRUD for user-owned budgets."""
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Budget.objects.select_related("category").all()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["start_date", "end_date", "amount", "created_at"]
    ordering = ["-start_date", "-created_at"]


# PUBLIC_INTERFACE
class RecurringRuleViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """CRUD for user-owned recurring rules."""
    serializer_class = RecurringRuleSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = RecurringRule.objects.select_related("category").all()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name", "start_date", "created_at"]
    ordering = ["name"]
