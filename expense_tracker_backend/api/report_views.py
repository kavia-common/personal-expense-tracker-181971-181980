from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Expense, Budget


def _parse_date(value: str | None) -> datetime | None:
    """Parse YYYY-MM-DD into date; returns None if invalid or missing."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()  # type: ignore[return-value]
    except Exception:
        return None


def _apply_expense_filters(qs, user, start_date, end_date, category_id):
    qs = qs.filter(user=user)
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    if category_id:
        qs = qs.filter(category_id=category_id)
    return qs


# PUBLIC_INTERFACE
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_summary(request):
    """
    Summarize expenses for the authenticated user.

    Query parameters:
      - start_date: YYYY-MM-DD (optional)
      - end_date: YYYY-MM-DD (optional)
      - group_by: 'category' | 'month' (optional; default: 'category')
      - category: category id to filter on (optional)

    Returns:
      200 OK with JSON:
      {
        "group_by": "category" | "month",
        "currency": "<currency-or-mixed>",
        "results": [
           { "group": "<category_name or YYYY-MM>", "total": "123.45", "category_id": 1? },
           ...
        ],
        "total": "456.78"
      }
    """
    user = request.user
    start_date = _parse_date(request.query_params.get("start_date"))
    end_date = _parse_date(request.query_params.get("end_date"))
    category_id = request.query_params.get("category")
    group_by = (request.query_params.get("group_by") or "category").lower()

    qs = Expense.objects.select_related("category").all()
    qs = _apply_expense_filters(qs, user, start_date, end_date, category_id)

    # Aggregate overall total
    overall_total = qs.aggregate(total=Sum("amount")).get("total") or Decimal("0")

    results: List[Dict[str, Any]] = []
    currency = None

    if group_by == "month":
        # Group by month (YYYY-MM) of expense date
        month_qs = (
            qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        for item in month_qs:
            month_val = item.get("month")
            # Serialize to YYYY-MM, handling None safely
            label = month_val.strftime("%Y-%m") if month_val else "Unknown"
            results.append(
                {
                    "group": label,
                    "total": str(item.get("total") or Decimal("0")),
                }
            )
    else:
        # Default: group by category (include uncategorized as "Uncategorized")
        cat_qs = (
            qs.annotate(
                category_name=F("category__name"),
            )
            .values("category_id", "category_name")
            .annotate(total=Sum("amount"))
            .order_by("category_name")
        )
        for item in cat_qs:
            name = item.get("category_name") or "Uncategorized"
            results.append(
                {
                    "group": name,
                    "category_id": item.get("category_id"),
                    "total": str(item.get("total") or Decimal("0")),
                }
            )

    # If all rows share the same currency in filtered set, return that; else "MIXED/VARIES"
    # We will compute by getting distinct currencies within the filtered queryset.
    distinct_currencies = qs.values_list("currency", flat=True).distinct()
    currencies = list(distinct_currencies)
    if len(currencies) == 1:
        currency = currencies[0]
    elif len(currencies) == 0:
        currency = None
    else:
        currency = "VARIES"

    payload = {
        "group_by": "month" if group_by == "month" else "category",
        "currency": currency,
        "results": results,
        "total": str(overall_total),
    }
    return Response(payload)


# PUBLIC_INTERFACE
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_budget_status(request):
    """
    Show budget utilization for the authenticated user by intersecting budgets with expenses in the same date window.

    Query parameters:
      - start_date: YYYY-MM-DD (optional)
      - end_date: YYYY-MM-DD (optional)
      - category: category id filter for both budgets and expenses (optional)

    Behavior:
      - For each budget that matches the filters (user + optional category + date window overlap),
        compute the sum of expenses within its [start_date, end_date] window and (if category is set on budget) the same category.
      - Return utilization and remaining amounts.

    Returns:
      200 OK with JSON:
      {
        "results": [
           {
             "budget_id": 1,
             "name": "...",
             "period": "monthly",
             "currency": "USD",
             "start_date": "YYYY-MM-DD",
             "end_date": "YYYY-MM-DD",
             "category_id": 3 | null,
             "category_name": "Groceries" | null,
             "budget_amount": "500.00",
             "spent": "320.00",
             "remaining": "180.00",
             "status": "under" | "over" | "met"
           },
           ...
        ]
      }
    """
    user = request.user
    start_date = _parse_date(request.query_params.get("start_date"))
    end_date = _parse_date(request.query_params.get("end_date"))
    category_filter = request.query_params.get("category")

    # Filter budgets for user, optionally by category and by overlapping date window with requested range if provided
    budgets = Budget.objects.select_related("category").filter(user=user)

    if category_filter:
        budgets = budgets.filter(category_id=category_filter)

    # If caller provided a date window, only include budgets that overlap it
    if start_date and end_date:
        # overlap if budget.start <= end AND budget.end >= start
        budgets = budgets.filter(start_date__lte=end_date, end_date__gte=start_date)
    elif start_date:
        budgets = budgets.filter(end_date__gte=start_date)
    elif end_date:
        budgets = budgets.filter(start_date__lte=end_date)

    results: List[Dict[str, Any]] = []

    # Pre-fetch all relevant expenses in one go to avoid N+1, then compute per-budget intersections
    exp_qs = Expense.objects.filter(user=user)
    if category_filter:
        exp_qs = exp_qs.filter(category_id=category_filter)
    # If caller provided a global window, it limits the expense search space; per-budget intersection further restricts it
    if start_date:
        exp_qs = exp_qs.filter(date__gte=start_date)
    if end_date:
        exp_qs = exp_qs.filter(date__lte=end_date)

    # Materialize to allow re-filtering in Python for remaining intersection logic
    # However, to keep memory lean, we will compute via DB for each budget with precise window/category combination.
    # There should be far fewer budgets than expenses, so per-budget aggregation query is acceptable here.

    for b in budgets:
        b_start = b.start_date
        b_end = b.end_date

        # Compute intersection window relative to global filters (already applied in exp_qs)
        # We use a fresh queryset per budget to ensure correct category scoping if budget has category.
        b_expenses = Expense.objects.filter(user=user, date__gte=b_start, date__lte=b_end)
        if category_filter:
            b_expenses = b_expenses.filter(category_id=category_filter)

        # If budget itself has a category, restrict to it regardless of global category filter (more specific)
        if b.category_id:
            b_expenses = b_expenses.filter(category_id=b.category_id)

        spent_total: Decimal = b_expenses.aggregate(total=Sum("amount")).get("total") or Decimal("0")
        remaining = (b.amount or Decimal("0")) - spent_total
        if remaining > 0:
            status = "under"
        elif remaining < 0:
            status = "over"
        else:
            status = "met"

        results.append(
            {
                "budget_id": b.id,
                "name": b.name,
                "period": b.period,
                "currency": b.currency,
                "start_date": str(b.start_date),
                "end_date": str(b.end_date),
                "category_id": b.category_id,
                "category_name": b.category.name if b.category_id else None,
                "budget_amount": str(b.amount),
                "spent": str(spent_total),
                "remaining": str(remaining),
                "status": status,
            }
        )

    return Response({"results": results})
