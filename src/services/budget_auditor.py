from typing import Any


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def audit_itinerary_budget(
    itinerary: dict[str, Any] | None,
    budget: float | int | None = None,
    currency: str = "INR",
) -> dict[str, Any]:
    """Audit estimated costs across days, activities, and routes against an optional budget."""
    data = itinerary if isinstance(itinerary, dict) else {}
    budget_limit = _to_float(budget)

    activity_total = 0.0
    route_total = 0.0
    priced_items = 0

    for day in data.get("days") or []:
        if not isinstance(day, dict):
            continue
        for act in day.get("activities") or []:
            if not isinstance(act, dict):
                continue
            cost = _to_float(
                act.get("estimated_cost")
                if act.get("estimated_cost") is not None
                else act.get("cost")
            )
            if cost is not None and cost >= 0:
                activity_total += cost
                priced_items += 1

            travel = act.get("travel_from_previous")
            if isinstance(travel, dict):
                leg_cost = _to_float(
                    travel.get("estimated_cost")
                    if travel.get("estimated_cost") is not None
                    else travel.get("cost")
                )
                if leg_cost is not None and leg_cost >= 0:
                    route_total += leg_cost
                    priced_items += 1

    for leg in data.get("route_legs") or []:
        if not isinstance(leg, dict):
            continue
        # Avoid double-counting if already summed via travel_from_previous
        if leg.get("_counted_in_travel"):
            continue
        leg_cost = _to_float(
            leg.get("estimated_cost")
            if leg.get("estimated_cost") is not None
            else leg.get("cost")
        )
        if leg_cost is not None and leg_cost >= 0:
            route_total += leg_cost
            priced_items += 1

    estimated_total = round(activity_total + route_total, 2)
    activity_total = round(activity_total, 2)
    route_total = round(route_total, 2)

    status = "unbudgeted"
    remaining: float | None = None
    overrun: float | None = None
    warnings: list[str] = []

    if budget_limit is not None and budget_limit > 0:
        diff = round(budget_limit - estimated_total, 2)
        if diff >= 0:
            status = "within_budget"
            remaining = diff
            overrun = 0.0
        else:
            status = "over_budget"
            remaining = 0.0
            overrun = abs(diff)
            warnings.append(
                f"Estimated trip cost ({currency} {estimated_total}) exceeds budget "
                f"({currency} {round(budget_limit, 2)}) by {currency} {overrun}."
            )
    elif priced_items == 0:
        status = "no_cost_data"

    audit_summary = {
        "currency": currency,
        "budget_limit": round(budget_limit, 2) if budget_limit is not None else None,
        "estimated_total": estimated_total,
        "activity_cost_total": activity_total,
        "route_cost_total": route_total,
        "remaining_budget": remaining,
        "overrun_amount": overrun,
        "priced_items": priced_items,
        "status": status,
        "warnings": warnings,
    }

    if isinstance(itinerary, dict):
        itinerary["budget_audit"] = audit_summary
        if warnings:
            existing = itinerary.get("warnings")
            merged = list(existing) if isinstance(existing, list) else []
            for w in warnings:
                if w not in merged:
                    merged.append(w)
            itinerary["warnings"] = merged

    return audit_summary
