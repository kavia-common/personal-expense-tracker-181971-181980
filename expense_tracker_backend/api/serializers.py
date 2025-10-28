from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Expense, Budget, RecurringRule

User = get_user_model()


class OwnedModelSerializer(serializers.ModelSerializer):
    """
    Base serializer that ensures the `user` field is always set to the request.user
    on create/update. The user field is read-only to clients.
    """

    user = serializers.PrimaryKeyRelatedField(read_only=True)

    def create(self, validated_data: dict[str, Any]) -> Any:
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)

    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        # Prevent user takeover attempts
        validated_data.pop("user", None)
        return super().update(instance, validated_data)


# PUBLIC_INTERFACE
class CategorySerializer(OwnedModelSerializer):
    """Serializer for Category objects tied to the authenticated user."""

    class Meta:
        model = Category
        fields = ["id", "name", "description", "is_active", "created_at", "updated_at", "user"]
        read_only_fields = ["id", "created_at", "updated_at", "user"]


# PUBLIC_INTERFACE
class ExpenseSerializer(OwnedModelSerializer):
    """Serializer for Expense with optional relations to Category and RecurringRule."""
    category = serializers.PrimaryKeyRelatedField(
        allow_null=True, required=False, queryset=Category.objects.all()
    )
    recurring_rule = serializers.PrimaryKeyRelatedField(
        allow_null=True, required=False, queryset=RecurringRule.objects.all()
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "amount",
            "currency",
            "description",
            "date",
            "category",
            "recurring_rule",
            "created_at",
            "updated_at",
            "user",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user"]

    def validate_category(self, value: Category | None) -> Category | None:
        # Ensure related objects belong to the same user
        if value is None:
            return value
        request = self.context.get("request")
        if request and request.user and value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid category.")
        return value

    def validate_recurring_rule(self, value: RecurringRule | None) -> RecurringRule | None:
        if value is None:
            return value
        request = self.context.get("request")
        if request and request.user and value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid recurring rule.")
        return value


# PUBLIC_INTERFACE
class BudgetSerializer(OwnedModelSerializer):
    """Serializer for Budget, optionally scoped to a Category."""
    category = serializers.PrimaryKeyRelatedField(
        allow_null=True, required=False, queryset=Category.objects.all()
    )

    class Meta:
        model = Budget
        fields = [
            "id",
            "name",
            "period",
            "amount",
            "currency",
            "start_date",
            "end_date",
            "category",
            "created_at",
            "updated_at",
            "user",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user"]

    def validate_category(self, value: Category | None) -> Category | None:
        if value is None:
            return value
        request = self.context.get("request")
        if request and request.user and value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid category.")
        return value


# PUBLIC_INTERFACE
class RecurringRuleSerializer(OwnedModelSerializer):
    """Serializer for RecurringRule with optional Category reference."""
    category = serializers.PrimaryKeyRelatedField(
        allow_null=True, required=False, queryset=Category.objects.all()
    )

    class Meta:
        model = RecurringRule
        fields = [
            "id",
            "name",
            "amount",
            "currency",
            "cadence",
            "start_date",
            "end_date",
            "description",
            "category",
            "created_at",
            "updated_at",
            "user",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user"]

    def validate_category(self, value: Category | None) -> Category | None:
        if value is None:
            return value
        request = self.context.get("request")
        if request and request.user and value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid category.")
        return value
