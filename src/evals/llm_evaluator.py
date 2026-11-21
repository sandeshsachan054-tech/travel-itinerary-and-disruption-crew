from typing import Any


def _normalize(value: Any) -> str:
    # Normalize strings for case-insensitive matching
    return str(value or "").strip().lower()


def _extract_itinerary_dict(payload: dict[str, Any] | None) -> dict[str, Any]:
    # Unwrap {"trip_id": ..., "itinerary": {...}} if passed a service/controller response
    if isinstance(payload, dict) and isinstance(payload.get("itinerary"), dict):
        return payload["itinerary"]
    return payload if isinstance(payload, dict) else {}


def evaluate_itinerary(
    payload: dict[str, Any] | None,
    available_spots: list[dict[str, Any]] | None = None,
    expected_days: int | None = None,
    expected_destination: str | None = None,
) -> dict[str, Any]:
    # Run fast deterministic checks for structure, grounding, duplicates, and timing
    itinerary = _extract_itinerary_dict(payload)
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    # Verify core itinerary container and day list
    days = itinerary.get("days")
    has_days = isinstance(days, list) and len(days) > 0
    add_check(
        "has_days",
        has_days,
        f"Found {len(days) if isinstance(days, list) else 0} day entries.",
    )

    # Check day count when an expected duration is provided
    if expected_days is not None and isinstance(days, list):
        add_check(
            "day_count_matches",
            len(days) == expected_days,
            f"Expected {expected_days} days, got {len(days)}.",
        )

    # Check destination consistency if expected destination is provided
    if expected_destination:
        actual_dest = _normalize(itinerary.get("destination"))
        target_dest = _normalize(expected_destination)
        add_check(
            "destination_matches",
            actual_dest == target_dest,
            f"Expected '{expected_destination}', got '{itinerary.get('destination')}'.",
        )

    # Build lookup of allowed spot names from discovered spots
    allowed_spots = {
        _normalize(spot.get("name"))
        for spot in (available_spots or [])
        if isinstance(spot, dict) and _normalize(spot.get("name"))
    }

    # Walk through activities to check grounding, duplicates, and time fields
    seen_names: set[str] = set()
    ungrounded_spots: list[str] = []
    duplicate_spots: list[str] = []
    missing_time_count = 0
    total_activities = 0

    for day in days if isinstance(days, list) else []:
        if not isinstance(day, dict):
            continue
        for act in day.get("activities") or []:
            if not isinstance(act, dict):
                continue
            total_activities += 1
            raw_name = act.get("name")
            norm_name = _normalize(raw_name)

            if norm_name:
                if norm_name in seen_names:
                    duplicate_spots.append(str(raw_name))
                else:
                    seen_names.add(norm_name)

                if allowed_spots and norm_name not in allowed_spots:
                    ungrounded_spots.append(str(raw_name))

            if not act.get("start_time") or not act.get("end_time"):
                missing_time_count += 1

    if allowed_spots:
        add_check(
            "spots_grounded",
            len(ungrounded_spots) == 0,
            "All planned activities match discovered spots."
            if not ungrounded_spots
            else f"Ungrounded activities: {', '.join(ungrounded_spots)}",
        )

    add_check(
        "no_duplicate_activities",
        len(duplicate_spots) == 0,
        "No duplicate activities found."
        if not duplicate_spots
        else f"Duplicate activities: {', '.join(duplicate_spots)}",
    )

    add_check(
        "schedule_times_present",
        total_activities > 0 and missing_time_count == 0,
        f"Checked {total_activities} activities; {missing_time_count} missing start/end time.",
    )

    # Compute overall pass rate and pass boolean
    passed_count = sum(1 for item in checks if item["passed"])
    total_count = len(checks)
    score = round(passed_count / total_count, 2) if total_count else 0.0

    return {
        "passed": all(item["passed"] for item in checks),
        "score": score,
        "passed_checks": passed_count,
        "total_checks": total_count,
        "checks": checks,
    }


def evaluate_batch(cases: list[dict[str, Any]]) -> dict[str, Any]:
    # Run evaluate_itinerary across multiple test cases and summarize results
    results = []
    for idx, case in enumerate(cases or [], start=1):
        case_id = case.get("id") or f"case_{idx}"
        report = evaluate_itinerary(
            payload=case.get("output"),
            available_spots=case.get("available_spots"),
            expected_days=case.get("expected_days"),
            expected_destination=case.get("expected_destination"),
        )
        results.append({"id": case_id, **report})

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r["passed"])
    avg_score = (
        round(sum(r["score"] for r in results) / total_cases, 2) if total_cases else 0.0
    )

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate": round(passed_cases / total_cases, 2) if total_cases else 0.0,
        "average_score": avg_score,
        "results": results,
    }
