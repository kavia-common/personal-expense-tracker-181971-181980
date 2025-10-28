from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation timestamp.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last updated timestamp.")

    class Meta:
        abstract = True


# PUBLIC_INTERFACE
class Category(TimeStampedModel):
    """A per-user category for classifying expenses and budgets."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        help_text="Owner of this category."
    )
    name = models.CharField(max_length=100, help_text="Category name (unique per user).")
    description = models.CharField(max_length=255, blank=True, default="", help_text="Optional category description.")
    is_active = models.BooleanField(default=True, help_text="Whether this category is active for the user.")

    class Meta:
        unique_together = (("user", "name"),)
        indexes = [
            models.Index(fields=["user", "name"], name="idx_category_user_name"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.user})"


# PUBLIC_INTERFACE
class Expense(TimeStampedModel):
    """An expense item belonging to a user, optionally categorized."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses",
        help_text="Owner of this expense."
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount of the expense.")
    currency = models.CharField(max_length=10, default="USD", help_text="Currency code, e.g., USD.")
    description = models.CharField(max_length=255, blank=True, default="", help_text="Optional description or memo.")
    date = models.DateField(help_text="Date the expense occurred.")
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="expenses",
        help_text="Optional category for the expense. Nullable; category deletions will not delete the expense."
    )
    # Optional link to recurring rule that generated this expense
    recurring_rule = models.ForeignKey(
        "RecurringRule",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_expenses",
        help_text="Optional recurring rule that generated this expense."
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"], name="idx_expense_user_date"),
            models.Index(fields=["user", "category"], name="idx_expense_user_category"),
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.amount} {self.currency} on {self.date} ({self.user})"


# PUBLIC_INTERFACE
class Budget(TimeStampedModel):
    """A per-user budget allocation for a period, optionally scoped to a category."""
    PERIOD_MONTHLY = "monthly"
    PERIOD_WEEKLY = "weekly"
    PERIOD_YEARLY = "yearly"
    PERIOD_CHOICES = [
        (PERIOD_WEEKLY, "Weekly"),
        (PERIOD_MONTHLY, "Monthly"),
        (PERIOD_YEARLY, "Yearly"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
        help_text="Owner of this budget."
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Budgeted amount for the period.")
    currency = models.CharField(max_length=10, default="USD", help_text="Currency code, e.g., USD.")
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default=PERIOD_MONTHLY, help_text="Budget period.")
    start_date = models.DateField(help_text="Start date for the budget period.")
    end_date = models.DateField(help_text="End date for the budget period.")
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="budgets",
        help_text="Optional category for the budget. Nullable; deletion won't remove the budget."
    )
    name = models.CharField(
        max_length=120,
        default="",
        blank=True,
        help_text="Optional label for the budget (e.g., 'Groceries Q1')."
    )

    class Meta:
        # Avoid duplicate overlapping same-named budget for same user/period/category/date-range tuple
        indexes = [
            models.Index(fields=["user", "period", "start_date", "end_date"], name="idx_budget_period_window"),
            models.Index(fields=["user", "category"], name="idx_budget_user_category"),
        ]
        ordering = ["-start_date", "-created_at"]

    def __str__(self) -> str:
        scope = self.category.name if self.category_id else "All categories"
        return f"{self.period} budget {self.amount} {self.currency} ({scope})"


# PUBLIC_INTERFACE
class RecurringRule(TimeStampedModel):
    """A per-user recurring expense rule to generate expenses automatically."""
    CADENCE_DAILY = "daily"
    CADENCE_WEEKLY = "weekly"
    CADENCE_MONTHLY = "monthly"
    CADENCE_YEARLY = "yearly"
    CADENCE_CHOICES = [
        (CADENCE_DAILY, "Daily"),
        (CADENCE_WEEKLY, "Weekly"),
        (CADENCE_MONTHLY, "Monthly"),
        (CADENCE_YEARLY, "Yearly"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_rules",
        help_text="Owner of this recurring rule."
    )
    name = models.CharField(max_length=120, help_text="A short name for the rule (per-user unique).")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Expense amount to generate.")
    currency = models.CharField(max_length=10, default="USD", help_text="Currency code, e.g., USD.")
    cadence = models.CharField(max_length=10, choices=CADENCE_CHOICES, help_text="Frequency of recurrence.")
    start_date = models.DateField(help_text="Date the recurrence starts.")
    end_date = models.DateField(null=True, blank=True, help_text="Optional end date of the recurrence.")
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recurring_rules",
        help_text="Optional category to associate generated expenses with."
    )
    description = models.CharField(max_length=255, blank=True, default="", help_text="Optional description.")

    class Meta:
        unique_together = (("user", "name"),)
        indexes = [
            models.Index(fields=["user", "name"], name="idx_rr_user_name"),
            models.Index(fields=["user", "cadence"], name="idx_rr_user_cadence"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.cadence}) - {self.user}"
