from django.contrib import admin
from .models import Category, Expense, Budget, RecurringRule


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_active", "created_at", "updated_at")
    search_fields = ("name", "user__username", "user__email")
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("amount", "currency", "date", "user", "category", "created_at")
    search_fields = ("description", "user__username", "user__email", "category__name")
    list_filter = ("currency", "category")
    date_hierarchy = "date"
    ordering = ("-date",)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("name", "period", "amount", "currency", "start_date", "end_date", "user", "category")
    search_fields = ("name", "user__username", "user__email", "category__name")
    list_filter = ("period", "currency", "category")
    date_hierarchy = "start_date"
    ordering = ("-start_date",)


@admin.register(RecurringRule)
class RecurringRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "cadence", "amount", "currency", "user", "category", "start_date", "end_date")
    search_fields = ("name", "description", "user__username", "user__email", "category__name")
    list_filter = ("cadence", "currency", "category")
    date_hierarchy = "start_date"
    ordering = ("name",)
