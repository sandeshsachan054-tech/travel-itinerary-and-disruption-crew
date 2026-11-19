
from datetime import date, timedelta
from typing import TypedDict
import inspect

from langgraph.graph import StateGraph, END

from .schemas import TripRequest
from .serpapi_tools import SerpApiTools
from .llm_client import GroqJSONClient


# =====================================================
# LANGGRAPH STATE
# =====================================================

class PlannerState(TypedDict, total=False):

    request: dict

    spots: list

    assignments: list

    itinerary: dict

    warnings: list


# =====================================================
# PLANNER AGENT
# =====================================================

class PlannerAgent:

    def __init__(self, tools=None, llm=None):

        self.tools = tools or SerpApiTools()

        self.llm = llm or GroqJSONClient()

        # Build LangGraph workflow
        workflow = StateGraph(PlannerState)

        workflow.add_node(
            "discover_spots",
            self.discover_spots
        )

        workflow.add_node(
            "organize_days",
            self.organize_days
        )

        workflow.add_node(
            "build_itinerary",
            self.build_itinerary
        )

        workflow.set_entry_point("discover_spots")

        workflow.add_edge(
            "discover_spots",
            "organize_days"
        )

        workflow.add_edge(
            "organize_days",
            "build_itinerary"
        )

        workflow.add_edge(
            "build_itinerary",
            END
        )

        self.graph = workflow.compile()

    # =================================================
    # HELPER 1: TIME CONVERSION
    # =================================================

    @staticmethod
    def time_to_minutes(value):

        hours, minutes = map(
            int,
            value.split(":")
        )

        return hours * 60 + minutes

    @staticmethod
    def minutes_to_time(value):

        if value < 0 or value >= 1440:
            return None

        hours, minutes = divmod(value, 60)

        return f"{hours:02d}:{minutes:02d}"

    # =================================================
    # HELPER 2: GPS COORDINATES
    # =================================================

    @staticmethod
    def get_coordinates(spot):

        latitude = spot.get("latitude")

        longitude = spot.get("longitude")

        if latitude is None or longitude is None:
            return None

        return f"{latitude},{longitude}"

    # =================================================
    # HELPER 3: ROUTE LOOKUP
    # Supports both updated and older tool signatures.
    # =================================================

    def fetch_route(
        self,
        origin,
        destination,
        travel_mode,
        origin_data_id=None,
        destination_data_id=None,
        origin_coords=None,
        destination_coords=None
    ):

        method = self.tools.get_route

        try:

            parameters = inspect.signature(
                method
            ).parameters

            supports_extra = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in parameters.values()
            )

        except (TypeError, ValueError):

            supports_extra = False
            parameters = {}

        if (
            supports_extra
            or "origin_data_id" in parameters
        ):

            return method(

                origin=origin,

                destination=destination,

                travel_mode=travel_mode,

                origin_data_id=origin_data_id,

                destination_data_id=destination_data_id,

                origin_coords=origin_coords,

                destination_coords=destination_coords

            )

        # Compatibility with the older get_route function
        return method(

            origin=origin,

            destination=destination,

            travel_mode=travel_mode

        )

    # =================================================
    # NODE 1: DISCOVER TOURIST SPOTS
    # =================================================

    def discover_spots(self, state):

        request = state["request"]

        destination = request["destination"]

        selected_spots = request.get(
            "selected_spots",
            []
        )

        interests = request.get(
            "interests",
            ["tourist attractions"]
        )

        warnings = list(
            state.get("warnings", [])
        )

        spots = []

        # ---------------------------------------------
        # CASE 1: USER SELECTED SPECIFIC PLACES
        # ---------------------------------------------

        if selected_spots:

            for name in selected_spots:

                spots.append({

                    "name": name,

                    "address": f"{name}, {destination}",

                    "category": "selected",

                    "source": "User"

                })

        # ---------------------------------------------
        # CASE 2: AUTOMATIC SPOT DISCOVERY
        # ---------------------------------------------

        else:

            for interest in interests:

                try:

                    results = self.tools.search_spots(

                        destination=destination,

                        query=interest,

                        limit=8

                    )

                    spots.extend(results)

                    print(
                        f"[SerpApi] Found {len(results)} "
                        f"spots for {interest}"
                    )

                except Exception as error:

                    warnings.append(
                        f"Spot discovery failed for "
                        f"{interest}: {error}"
                    )

        # ---------------------------------------------
        # REMOVE DUPLICATE PLACES
        # ---------------------------------------------

        unique_spots = {}

        for spot in spots:

            name = spot.get("name")

            if name:

                unique_spots[name.lower()] = spot

        spots = list(
            unique_spots.values()
        )

        # Maximum 3 places per day for MVP
        spots = spots[:request["days"] * 3]

        if not spots:

            warnings.append(
                "No tourist spots found for this destination."
            )

        return {

            "spots": spots,

            "warnings": warnings

        }

    # =================================================
    # NODE 2: ORGANIZE PLACES USING GROQ
    # =================================================

    def organize_days(self, state):

        request = state["request"]

        spots = state.get(
            "spots",
            []
        )

        total_days = request["days"]

        assignments = [
            [] for _ in range(total_days)
        ]

        if not spots:

            return {
                "assignments": assignments
            }

        spot_names = [
            spot["name"] for spot in spots
        ]

        system_prompt = """

        You are an intelligent travel itinerary planner.

        Organize tourist places into a day-wise travel plan.

        STRICT RULES:

        1. Use only the places supplied in the input.
        2. Never invent tourist locations.
        3. Never repeat a location.
        4. Distribute locations across all requested days.
        5. Keep the daily schedule balanced.
        6. Consider user interests.
        7. Return valid JSON only.

        OUTPUT FORMAT:

        {
            "days": [
                {
                    "day": 1,
                    "spots": [
                        "Hawa Mahal",
                        "City Palace"
                    ]
                },
                {
                    "day": 2,
                    "spots": []
                }
            ]
        }

        """

        ai_result = None

        # ---------------------------------------------
        # GROQ LLM CALL
        # ---------------------------------------------

        try:

            ai_result = self.llm.generate_json(

                system_prompt,

                {

                    "destination": request["destination"],

                    "number_of_days": total_days,

                    "interests": request.get(
                        "interests",
                        []
                    ),

                    "available_spots": spot_names

                }

            )

        except Exception as error:

            print(
                f"[Groq] LLM unavailable: {error}"
            )

        # ---------------------------------------------
        # VALIDATE LLM OUTPUT
        # ---------------------------------------------

        if isinstance(ai_result, dict):

            lookup = {
                name.lower(): name
                for name in spot_names
            }

            used = set()

            for day_data in ai_result.get("days", []):

                if not isinstance(day_data, dict):
                    continue

                try:

                    day_number = int(
                        day_data.get("day", 0)
                    )

                except (TypeError, ValueError):

                    continue

                if not (
                    1 <= day_number <= total_days
                ):
                    continue

                day_spots = day_data.get(
                    "spots",
                    []
                )

                if not isinstance(day_spots, list):
                    continue

                for name in day_spots:

                    if not isinstance(name, str):
                        continue

                    normalized = name.lower()

                    if (
                        normalized in lookup
                        and normalized not in used
                    ):

                        assignments[
                            day_number - 1
                        ].append(
                            lookup[normalized]
                        )

                        used.add(normalized)

            # Add all places the LLM forgot
            for name in spot_names:

                if name.lower() not in used:

                    smallest_day = min(

                        range(total_days),

                        key=lambda i: len(
                            assignments[i]
                        )

                    )

                    assignments[
                        smallest_day
                    ].append(name)

            print(
                "[Groq] Places organized successfully."
            )

            return {

                "assignments": assignments

            }

        # ---------------------------------------------
        # FALLBACK WITHOUT GROQ
        # ---------------------------------------------

        print(
            "[Planner] Using deterministic fallback."
        )

        for name in spot_names:

            smallest_day = min(

                range(total_days),

                key=lambda i: len(
                    assignments[i]
                )

            )

            assignments[
                smallest_day
            ].append(name)

        return {

            "assignments": assignments

        }

    # =================================================
    # NODE 3: BUILD HOURLY ITINERARY
    # =================================================

    def build_itinerary(self, state):

        request = state["request"]

        spots = state.get(
            "spots",
            []
        )

        assignments = state.get(
            "assignments",
            []
        )

        warnings = list(
            state.get("warnings", [])
        )

        # ---------------------------------------------
        # DATE SETTINGS
        # ---------------------------------------------

        if request.get("start_date"):

            start_date = date.fromisoformat(
                request["start_date"]
            )

        else:

            start_date = date.today()

        # ---------------------------------------------
        # TIME SETTINGS
        # ---------------------------------------------

        daily_start = self.time_to_minutes(
            request.get(
                "daily_start_time",
                "09:00"
            )
        )

        daily_end = self.time_to_minutes(
            request.get(
                "daily_end_time",
                "20:00"
            )
        )

        visit_duration = request.get(
            "visit_duration_minutes",
            90
        )

        travel_mode = request.get(
            "travel_mode",
            "driving"
        )

        # ---------------------------------------------
        # INITIAL LOCATION
        # ---------------------------------------------

        start_location = (
            request.get("start_location")
            or request["destination"]
        )

        all_route_legs = []

        all_days = []

        spot_lookup = {

            spot["name"].lower(): spot

            for spot in spots

        }

        # =============================================
        # GENERATE EACH DAY
        # =============================================

        for day_number, day_spots in enumerate(
            assignments,
            start=1
        ):

            print(
                f"[Planner] Building Day {day_number}"
            )

            current_time = daily_start

            current_origin = start_location

            origin_data_id = None

            origin_coords = None

            # When a route is unavailable,
            # subsequent times become provisional.
            timing_blocked = False

            activities = []

            # -----------------------------------------
            # EACH TOURIST SPOT
            # -----------------------------------------

            for index, spot_name in enumerate(
                day_spots,
                start=1
            ):

                spot = spot_lookup.get(
                    spot_name.lower()
                )

                if spot is None:
                    continue

                destination = (

                    spot.get("address")

                    or f"{spot_name}, {request['destination']}"

                )

                destination_data_id = spot.get(
                    "data_id"
                )

                destination_coords = (
                    self.get_coordinates(spot)
                )

                route_id = (
                    f"route-d{day_number}-s{index}"
                )

                activity_id = (
                    f"activity-d{day_number}-s{index}"
                )

                route = None

                # -------------------------------------
                # SERPAPI ROUTE LOOKUP
                # -------------------------------------

                try:

                    route = self.fetch_route(

                        origin=current_origin,

                        destination=destination,

                        travel_mode=travel_mode,

                        origin_data_id=origin_data_id,

                        destination_data_id=destination_data_id,

                        origin_coords=origin_coords,

                        destination_coords=destination_coords

                    )

                except Exception as error:

                    warnings.append(

                        f"Route unavailable: "
                        f"{current_origin} -> {destination}: "
                        f"{error}"

                    )

                    print(
                        f"[Route Error] {current_origin} "
                        f"-> {destination}: {error}"
                    )

                # -------------------------------------
                # NORMALIZE ROUTE DATA
                # -------------------------------------

                if not isinstance(route, dict):
                    route = {}

                duration = route.get(
                    "duration_minutes"
                )

                if duration is not None:

                    try:

                        duration = max(
                            0,
                            int(float(duration))
                        )

                    except (TypeError, ValueError):

                        duration = None

                # -------------------------------------
                # ROUTE VERIFICATION
                # -------------------------------------

                if duration is None:

                    timing_blocked = True

                    route_status = "unverified"

                    warnings.append(

                        f"Timing is provisional for "
                        f"{spot_name}; route duration "
                        f"could not be verified."

                    )

                else:

                    route_status = "verified"

                # -------------------------------------
                # CREATE ROUTE LEG
                # -------------------------------------

                route_leg = {

                    "route_id": route_id,

                    "day": day_number,

                    "from": current_origin,

                    "to": destination,

                    "from_data_id": origin_data_id,

                    "to_data_id": destination_data_id,

                    "from_coords": origin_coords,

                    "to_coords": destination_coords,

                    "travel_mode": travel_mode,

                    "distance_meters": route.get(
                        "distance_meters"
                    ),

                    "duration_seconds": route.get(
                        "duration_seconds"
                    ),

                    "duration_minutes": duration,

                    "formatted_distance": route.get(
                        "formatted_distance"
                    ),

                    "formatted_duration": route.get(
                        "formatted_duration"
                    ),

                    "cost_amount": route.get(
                        "cost_amount"
                    ),

                    "currency": route.get(
                        "currency"
                    ),

                    "status": route_status

                }

                all_route_legs.append(
                    route_leg
                )

                # -------------------------------------
                # CREATE ACTIVITY TIME SLOT
                # -------------------------------------

                if not timing_blocked:

                    current_time += duration

                    activity_start = current_time

                    activity_end = (
                        activity_start + visit_duration
                    )

                    start_time = self.minutes_to_time(
                        activity_start
                    )

                    end_time = self.minutes_to_time(
                        activity_end
                    )

                    timing_status = "verified_route"

                    if (
                        activity_start > daily_end
                        or activity_end > daily_end
                    ):

                        warnings.append(
                            f"Day {day_number} exceeds "
                            "the preferred daily end time."
                        )

                    current_time = activity_end

                else:

                    start_time = None

                    end_time = None

                    timing_status = (
                        "needs_route_confirmation"
                    )

                # -------------------------------------
                # CREATE ACTIVITY
                # -------------------------------------

                activity = {

                    "activity_id": activity_id,

                    "name": spot_name,

                    "address": destination,

                    "category": spot.get(
                        "category"
                    ),

                    "rating": spot.get(
                        "rating"
                    ),

                    "data_id": destination_data_id,

                    "latitude": spot.get(
                        "latitude"
                    ),

                    "longitude": spot.get(
                        "longitude"
                    ),

                    "start_time": start_time,

                    "end_time": end_time,

                    "duration_minutes": visit_duration,

                    "estimated_cost": None,

                    "incoming_route_id": route_id,

                    "status": "planned",

                    "timing_status": timing_status

                }

                activities.append(
                    activity
                )

                # -------------------------------------
                # UPDATE ORIGIN FOR NEXT ROUTE
                # -------------------------------------

                current_origin = destination

                origin_data_id = destination_data_id

                origin_coords = destination_coords

            # -----------------------------------------
            # DAY OBJECT
            # -----------------------------------------

            day_plan = {

                "day": day_number,

                "date": (

                    start_date + timedelta(
                        days=day_number - 1
                    )

                ).isoformat(),

                "activities": activities

            }

            all_days.append(
                day_plan
            )

        # =============================================
        # FINAL ITINERARY
        # =============================================

        itinerary = {

            "itinerary_id": (
                f"trip-{start_date.isoformat()}-{id(state)}"
            ),

            "destination": request["destination"],

            "start_location": start_location,

            "start_date": start_date.isoformat(),

            "days": all_days,

            "route_legs": all_route_legs,

            "travel_mode": travel_mode,

            "interests": request.get(
                "interests",
                []
            ),

            "daily_start_time": request.get(
                "daily_start_time",
                "09:00"
            ),

            "daily_end_time": request.get(
                "daily_end_time",
                "20:00"
            ),

            "visit_duration_minutes": visit_duration,

            "currency": request.get(
                "currency",
                "INR"
            ),

            "budget_total": None,

            "budget_status": "pending_auditor",

            "warnings": list(
                dict.fromkeys(warnings)
            ),

            "audit_required": True

        }

        print(
            "[Planner] Itinerary generation completed."
        )

        return {

            "itinerary": itinerary

        }

    # =================================================
    # PUBLIC FUNCTION: PLAN TRIP
    # =================================================

    def plan_trip(self, request):

        print("\n========== PLANNER AGENT ==========\n")

        # ---------------------------------------------
        # VALIDATE REQUEST
        # ---------------------------------------------

        if isinstance(request, TripRequest):

            request = request.model_dump(
                mode="json"
            )

        else:

            request = TripRequest.model_validate(
                request
            ).model_dump(
                mode="json"
            )

        print(
            f"[Planner] Destination: {request['destination']}"
        )

        print(
            f"[Planner] Total days: {request['days']}"
        )

        # ---------------------------------------------
        # INITIAL STATE
        # ---------------------------------------------

        initial_state = {

            "request": request,

            "spots": [],

            "assignments": [],

            "warnings": []

        }

        # ---------------------------------------------
        # RUN LANGGRAPH
        # ---------------------------------------------

        result = self.graph.invoke(
            initial_state
        )

        # ---------------------------------------------
        # RETURN FINAL ITINERARY
        # ---------------------------------------------

        itinerary = result["itinerary"]

        print(
            "\n[Planner] Successfully generated itinerary."
        )

        print(
            f"[Planner] Days created: {len(itinerary['days'])}"
        )

        print(
            f"[Planner] Routes found: "
            f"{sum(1 for r in itinerary['route_legs'] if r['status'] == 'verified')}"
        )

        print(
            f"[Planner] Unverified routes: "
            f"{sum(1 for r in itinerary['route_legs'] if r['status'] == 'unverified')}"
        )

        print(
            "\n===================================\n"
        )

        return itinerary
