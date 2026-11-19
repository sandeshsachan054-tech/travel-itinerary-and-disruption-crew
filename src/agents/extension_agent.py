from datetime import date, timedelta

from .serpapi_tools import SerpApiTools
from .planner_agent import PlannerAgent


class ExtensionAgent:

    def __init__(self, tools=None, planner=None):

        self.tools = tools or SerpApiTools()

        self.planner = planner or PlannerAgent(
            tools=self.tools
        )

    def extend_trip(
        self,
        itinerary,
        new_total_days,
        interests=None
    ):

        current_days = len(itinerary["days"])

        if new_total_days <= current_days:

            raise ValueError(
                "New duration must be greater than existing duration."
            )

        extra_days = new_total_days - current_days

        destination = itinerary["destination"]

        interests = (
            interests
            or itinerary.get("interests")
            or ["tourist attractions"]
        )

        existing_names = {

            activity["name"].lower()

            for day in itinerary["days"]

            for activity in day["activities"]

        }

        # Find new tourist places
        new_spots = []

        for interest in interests:

            try:

                results = self.tools.search_spots(

                    destination=destination,

                    query=interest,

                    limit=10

                )

                for spot in results:

                    name = spot.get("name", "")

                    if (
                        name
                        and name.lower() not in existing_names
                    ):

                        new_spots.append(name)

                        existing_names.add(name.lower())

            except Exception:
                continue

            if len(new_spots) >= extra_days * 3:
                break

        new_spots = new_spots[:extra_days * 3]

        if not new_spots:

            raise ValueError(
                "No new verified spots found for trip extension."
            )

        # Get the last scheduled active location
        last_active = None

        for day in reversed(itinerary["days"]):

            for activity in reversed(day["activities"]):

                if activity.get("status") != "cancelled":

                    last_active = activity

                    break

            if last_active:
                break

        last_date = date.fromisoformat(
            itinerary["days"][-1]["date"]
        )

        extension_start_date = (
            last_date + timedelta(days=1)
        )

        start_location = (

            last_active["address"]
            if last_active
            else destination

        )

        extension_request = {

            "destination": destination,

            "days": extra_days,

            "start_date": extension_start_date.isoformat(),

            "start_location": start_location,

            "interests": interests,

            "selected_spots": new_spots,

            "daily_start_time": itinerary.get(
                "daily_start_time", "09:00"
            ),

            "daily_end_time": itinerary.get(
                "daily_end_time", "20:00"
            ),

            "visit_duration_minutes": itinerary.get(
                "visit_duration_minutes", 90
            ),

            "travel_mode": itinerary.get(
                "travel_mode", "driving"
            ),

            "currency": itinerary.get(
                "currency", "INR"
            )

        }

        new_itinerary = self.planner.plan_trip(
            extension_request
        )

        # Shift day numbers and route IDs
        route_id_map = {}

        for day in new_itinerary["days"]:

            old_day = day["day"]

            day["day"] += current_days

            for index, activity in enumerate(
                day["activities"],
                start=1
            ):

                old_id = activity.get(
                    "incoming_route_id"
                )

                new_id = (
                    f"route-d{day['day']}-s{index}"
                )

                if old_id:
                    route_id_map[old_id] = new_id

                activity["incoming_route_id"] = new_id

        for route in new_itinerary["route_legs"]:

            old_id = route["route_id"]

            old_day = route["day"]

            route["day"] = old_day + current_days

            route["route_id"] = route_id_map.get(
                old_id,
                route["route_id"]
            )

        # Combine old and new itinerary
        itinerary["days"].extend(
            new_itinerary["days"]
        )

        itinerary["route_legs"].extend(
            new_itinerary["route_legs"]
        )

        itinerary.setdefault(
            "warnings", []
        ).extend(
            new_itinerary.get("warnings", [])
        )

        itinerary["budget_total"] = None

        itinerary["budget_status"] = "pending_auditor"

        itinerary["audit_required"] = True

        itinerary["trip_extension"] = {

            "previous_days": current_days,

            "new_total_days": new_total_days,

            "added_days": extra_days,

            "new_spots": new_spots

        }

        return itinerary