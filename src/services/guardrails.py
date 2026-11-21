from typing import Any

# Simple list of phrases often used in prompt-injection attempts
BLOCKED_PHRASES = (
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "developer message",
    "jailbreak",
    "reveal your instructions",
)


def _to_dict(request_obj: Any) -> dict[str, Any]:
    # Convert Pydantic models or dicts into a plain dictionary
    if hasattr(request_obj, "model_dump"):
        return request_obj.model_dump()
    if isinstance(request_obj, dict):
        return request_obj
    raise ValueError("Request must be a dictionary or Pydantic model.")


def _has_blocked_phrase(text: Any) -> bool:
    # Return True if text contains any known prompt-injection phrase
    cleaned = str(text or "").lower()
    return any(phrase in cleaned for phrase in BLOCKED_PHRASES)


def _is_number(value: Any) -> bool:
    # In Python bool is a subclass of int, so exclude bools explicitly
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_trip_request(request_data: Any) -> dict[str, Any]:
    # Validate incoming trip request fields before calling the planner
    data = _to_dict(request_obj=request_data)

    destination = str(data.get("destination") or "").strip()
    if not destination:
        raise ValueError("Destination is required.")
    if _has_blocked_phrase(destination):
        raise ValueError("Destination contains blocked instructions.")

    start_location = data.get("start_location")
    if start_location and _has_blocked_phrase(start_location):
        raise ValueError("Start location contains blocked instructions.")

    days = data.get("days")
    if days is not None and (not _is_number(days) or days < 1 or days > 30):
        raise ValueError("Days must be between 1 and 30.")

    visit_minutes = data.get("visit_duration_minutes")
    if visit_minutes is not None and (
        not _is_number(visit_minutes) or visit_minutes < 15 or visit_minutes > 720
    ):
        raise ValueError("Visit duration must be between 15 and 720 minutes.")

    budget = data.get("budget")
    if budget is not None and (not _is_number(budget) or budget < 0):
        raise ValueError("Budget cannot be negative.")

    return data


def _collect_spot_names(available_spots: list[dict[str, Any]] | None) -> set[str]:
    # Build a lowercase set of valid spot names for quick lookup
    names: set[str] = set()
    for spot in available_spots or []:
        if isinstance(spot, dict):
            name = str(spot.get("name") or "").strip().lower()
            if name:
                names.add(name)
    return names


def _record_issue(
    message: str,
    warnings: list[str],
    strict: bool,
) -> None:
    # Either raise an error (strict mode) or record a warning once
    if strict:
        raise ValueError(message)
    if message not in warnings:
        warnings.append(message)


def validate_itinerary_output(
    itinerary: dict[str, Any] | None,
    available_spots: list[dict[str, Any]] | None = None,
    strict_grounding: bool = False,
) -> dict[str, Any]:
    # Check that the itinerary has days and no duplicate or unknown spots
    if not isinstance(itinerary, dict):
        raise ValueError("Itinerary must be a dictionary.")

    days = itinerary.get("days")
    if not isinstance(days, list) or len(days) == 0:
        raise ValueError("Itinerary must have at least one day.")

    allowed_spots = _collect_spot_names(available_spots)
    seen_spots: set[str] = set()
    warnings: list[str] = list(itinerary.get("warnings") or [])

    for day in days:
        if not isinstance(day, dict):
            continue
        for activity in day.get("activities") or []:
            if not isinstance(activity, dict):
                continue

            spot_name = str(activity.get("name") or "").strip()
            key = spot_name.lower()
            if not key:
                continue

            # Check for duplicate activities across days
            if key in seen_spots:
                _record_issue(
                    f"Duplicate activity: {spot_name}",
                    warnings,
                    strict_grounding,
                )
            else:
                seen_spots.add(key)

            # Check if the activity matches a discovered spot
            if allowed_spots and key not in allowed_spots:
                _record_issue(
                    f"Activity not in discovered spots: {spot_name}",
                    warnings,
                    strict_grounding,
                )

    itinerary["warnings"] = warnings
    return itinerary

