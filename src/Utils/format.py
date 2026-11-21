from typing import Any

NOISY_KEYS = {
    "place_id",
    "data_id",
    "from_data_id",
    "to_data_id",
    "latitude",
    "longitude",
    "lat",
    "lng",
    "from_coords",
    "to_coords",
    "audit_required",
    "source",
}


def short_id(raw_id: Any) -> str:
    value = str(raw_id or "").strip()
    return value.split("-")[-1] if "-" in value else value


def clean_data(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: clean_data(v)
            for k, v in data.items()
            if k not in NOISY_KEYS and v is not None
        }
    if isinstance(data, list):
        return [clean_data(item) for item in data]
    return data


def format_spots(spots: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [
        {
            "name": s.get("name"),
            "address": s.get("address"),
            "rating": s.get("rating"),
            "reviews": s.get("reviews"),
            "category": s.get("category"),
        }
        for s in (spots or [])
        if isinstance(s, dict)
    ]


def format_itinerary(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    legs = {
        str(leg["route_id"]): leg
        for leg in (raw.get("route_legs") or [])
        if isinstance(leg, dict) and leg.get("route_id")
    }

    days = []
    for day in raw.get("days") or []:
        day_num = day.get("day")
        activities = []

        for i, act in enumerate(day.get("activities") or [], start=1):
            leg = legs.get(str(act.get("incoming_route_id")), {})
            travel = (
                {
                    "route_id": f"d{day_num}-r{i}",
                    "from": leg.get("from"),
                    "distance": leg.get("formatted_distance"),
                    "duration": leg.get("formatted_duration"),
                    "status": leg.get("status", "unverified"),
                }
                if leg
                else None
            )

            item = {
                "activity_id": f"d{day_num}-a{i}",
                "name": act.get("name"),
                "address": act.get("address"),
                "rating": act.get("rating"),
                "start_time": act.get("start_time"),
                "end_time": act.get("end_time"),
                "duration_minutes": act.get("duration_minutes"),
                "travel_from_previous": travel,
                "status": act.get("status", "planned"),
            }
            if act.get("timing_status") and act.get("timing_status") != "verified_route":
                item["timing_status"] = act["timing_status"]

            activities.append(item)

        days.append({
            "day": day_num,
            "date": day.get("date"),
            "activities": activities,
        })

    warnings = list(dict.fromkeys(raw.get("warnings") or []))

    return {
        "destination": raw.get("destination"),
        "start_location": raw.get("start_location"),
        "start_date": raw.get("start_date"),
        "travel_mode": raw.get("travel_mode"),
        "daily_schedule": {
            "start_time": raw.get("daily_start_time"),
            "end_time": raw.get("daily_end_time"),
            "default_visit_minutes": raw.get("visit_duration_minutes"),
        },
        "days": days,
        "warnings": warnings,
    }


def format_trip(storage_id: str, raw_itinerary: dict[str, Any]) -> dict[str, Any]:
    return {
        "trip_id": short_id(storage_id),
        "itinerary": format_itinerary(raw_itinerary),
    }


def format_response(data: Any, message: str | None = None) -> dict[str, Any]:
    res: dict[str, Any] = {"data": clean_data(data)}
    if message:
        res["message"] = message
    return res
