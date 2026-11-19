from copy import deepcopy

from .serpapi_tools import SerpApiTools


class DisruptionAgent:

    def __init__(self, tools=None):

        self.tools = tools or SerpApiTools()

    @staticmethod
    def _to_minutes(value):

        hours, minutes = map(int, value.split(":"))

        return hours * 60 + minutes

    @staticmethod
    def _to_time(value):

        if value < 0 or value >= 1440:
            return None

        hours, minutes = divmod(value, 60)

        return f"{hours:02d}:{minutes:02d}"

    # -----------------------------------------------
    # RECALCULATE AFFECTED DAY AFTER ROUTE CHANGE
    # -----------------------------------------------

    def recalculate_day(self, itinerary, day_number):

        day = next(
            (
                d for d in itinerary["days"]
                if d["day"] == day_number
            ),
            None
        )

        if day is None:
            return

        routes = {
            route["route_id"]: route
            for route in itinerary.get("route_legs", [])
            if route.get("day") == day_number
        }

        current_time = self._to_minutes(
            itinerary.get("daily_start_time", "09:00")
        )

        blocked = False

        for activity in day["activities"]:

            if activity.get("status") == "cancelled":
                activity["start_time"] = None
                activity["end_time"] = None
                continue

            route = routes.get(
                activity.get("incoming_route_id")
            )

            if (
                blocked
                or route is None
                or route.get("status") == "cancelled"
                or route.get("duration_minutes") is None
            ):

                activity["start_time"] = None
                activity["end_time"] = None

                activity["timing_status"] = (
                    "needs_route_confirmation"
                )

                blocked = True

                continue

            current_time += route["duration_minutes"]

            start = current_time

            end = start + activity.get(
                "duration_minutes", 90
            )

            activity["start_time"] = self._to_time(start)

            activity["end_time"] = self._to_time(end)

            activity["timing_status"] = "verified_route"

            current_time = end

    # -----------------------------------------------
    # ROUTE CANCELLATION AND REROUTING
    # -----------------------------------------------

    def cancel_route(self, itinerary, route_id):

        updated = deepcopy(itinerary)

        target = next(
            (
                r for r in updated.get("route_legs", [])
                if r["route_id"] == route_id
            ),
            None
        )

        if target is None:

            raise ValueError(
                f"Route {route_id} not found"
            )

        old_mode = target["travel_mode"]

        alternative_modes = [
            "transit",
            "driving",
            "two_wheeler",
            "walking",
            "cycling"
        ]

        alternative_modes = [
            mode for mode in alternative_modes
            if mode != old_mode
        ]

        replacement = None

        for mode in alternative_modes:

            try:

                candidate = self.tools.get_route(

                    origin=target["from"],

                    destination=target["to"],

                    travel_mode=mode

                )

                if candidate.get("duration_minutes") is not None:

                    replacement = candidate

                    break

            except Exception:
                continue

        if replacement:

            preserved_id = target["route_id"]

            preserved_day = target["day"]

            target.update(replacement)

            target["route_id"] = preserved_id

            target["day"] = preserved_day

            target["original_travel_mode"] = old_mode

            target["status"] = "rerouted"

            message = (
                f"Route changed from {old_mode} "
                f"to {replacement['travel_mode']}."
            )

        else:

            target["status"] = "cancelled"

            target["duration_minutes"] = None

            target["cost_amount"] = None

            message = (
                "No verified alternative transport route found. "
                "Manual route selection is required."
            )

        self.recalculate_day(
            updated,
            target["day"]
        )

        updated.setdefault("warnings", []).append(
            message
        )

        updated["budget_total"] = None

        updated["budget_status"] = "pending_auditor"

        updated["audit_required"] = True

        updated["last_disruption"] = {

            "type": "route_cancellation",

            "route_id": route_id,

            "result": target["status"],

            "message": message

        }

        return updated

    # -----------------------------------------------
    # REBUILD ROUTES FOR ONE DAY
    # -----------------------------------------------

    def rebuild_day_routes(self, itinerary, day_number):

        day = next(
            (
                d for d in itinerary["days"]
                if d["day"] == day_number
            ),
            None
        )

        if day is None:
            return itinerary

        old_routes = [
            r for r in itinerary.get("route_legs", [])
            if r.get("day") != day_number
        ]

        new_routes = []

        active_activities = [
            activity for activity in day["activities"]
            if activity.get("status") != "cancelled"
        ]

        origin = (
            itinerary.get("start_location")
            or itinerary["destination"]
        )

        current_time = self._to_minutes(
            itinerary.get("daily_start_time", "09:00")
        )

        blocked = False

        mode = itinerary.get(
            "travel_mode", "driving"
        )

        for index, activity in enumerate(
            active_activities,
            start=1
        ):

            route_id = (
                f"route-d{day_number}-s{index}"
            )

            destination = activity["address"]

            try:

                route = self.tools.get_route(

                    origin=origin,

                    destination=destination,

                    travel_mode=mode

                )

            except Exception:

                route = {
                    "duration_minutes": None,
                    "duration_seconds": None,
                    "distance_meters": None,
                    "formatted_duration": None,
                    "cost_amount": None,
                    "currency": None
                }

            duration = route.get("duration_minutes")

            if blocked or duration is None:

                status = "unverified"

                activity["start_time"] = None

                activity["end_time"] = None

                activity["timing_status"] = (
                    "needs_route_confirmation"
                )

                blocked = True

            else:

                current_time += duration

                activity["start_time"] = self._to_time(
                    current_time
                )

                activity["end_time"] = self._to_time(
                    current_time + activity.get(
                        "duration_minutes", 90
                    )
                )

                activity["timing_status"] = "verified_route"

                current_time += activity.get(
                    "duration_minutes", 90
                )

                status = "verified"

            activity["incoming_route_id"] = route_id

            new_routes.append({

                "route_id": route_id,

                "day": day_number,

                "from": origin,

                "to": destination,

                "travel_mode": mode,

                "distance_meters": route.get(
                    "distance_meters"
                ),

                "duration_seconds": route.get(
                    "duration_seconds"
                ),

                "duration_minutes": duration,

                "formatted_duration": route.get(
                    "formatted_duration"
                ),

                "cost_amount": route.get(
                    "cost_amount"
                ),

                "currency": route.get("currency"),

                "status": status

            })

            origin = destination

        for activity in day["activities"]:

            if activity.get("status") == "cancelled":

                activity["incoming_route_id"] = None

                activity["start_time"] = None

                activity["end_time"] = None

        updated_routes = old_routes + new_routes

        itinerary["route_legs"] = updated_routes

        if any(
            r["status"] == "unverified"
            for r in new_routes
        ):

            itinerary.setdefault("warnings", []).append(
                f"Day {day_number} contains unverified routes."
            )

        return itinerary

    # -----------------------------------------------
    # ACTIVITY CANCELLATION AND REPLACEMENT
    # -----------------------------------------------

    def cancel_activity(
        self,
        itinerary,
        activity_id,
        replacement_query=None
    ):

        updated = deepcopy(itinerary)

        target = None

        target_day = None

        for day in updated["days"]:

            for activity in day["activities"]:

                if activity["activity_id"] == activity_id:

                    target = activity

                    target_day = day["day"]

                    break

            if target:
                break

        if target is None:

            raise ValueError(
                f"Activity {activity_id} not found"
            )

        original_name = target["name"]

        category = (
            replacement_query
            or target.get("category")
            or "tourist attractions"
        )

        if category == "selected":
            category = "tourist attractions"

        existing_names = {

            activity["name"].lower()

            for day in updated["days"]

            for activity in day["activities"]

            if activity.get("status") != "cancelled"

        }

        replacement = None

        try:

            candidates = self.tools.search_spots(

                destination=updated["destination"],

                query=category,

                limit=10

            )

            for candidate in candidates:

                name = candidate.get("name", "")

                if name and name.lower() not in existing_names:

                    replacement = candidate

                    break

        except Exception as exc:

            updated.setdefault("warnings", []).append(
                f"Replacement discovery failed: {exc}"
            )

        if replacement:

            target.update({

                "name": replacement["name"],

                "address": (
                    replacement.get("address")
                    or replacement["name"]
                ),

                "category": replacement.get("category"),

                "rating": replacement.get("rating"),

                "replacement_for": original_name,

                "status": "replacement",

                "start_time": None,

                "end_time": None,

                "timing_status": "needs_recalculation"

            })

            message = (
                f"{original_name} replaced with "
                f"{replacement['name']}."
            )

        else:

            target["status"] = "cancelled"

            target["start_time"] = None

            target["end_time"] = None

            message = (
                f"{original_name} cancelled. "
                "No verified replacement was found."
            )

        updated = self.rebuild_day_routes(
            updated,
            target_day
        )

        updated.setdefault("warnings", []).append(message)

        updated["budget_total"] = None

        updated["budget_status"] = "pending_auditor"

        updated["audit_required"] = True

        updated["last_disruption"] = {

            "type": "activity_cancellation",

            "activity_id": activity_id,

            "original_activity": original_name,

            "result": (
                "replaced" if replacement else "cancelled"
            ),

            "message": message

        }

        return updated