from src.agents.schemas import TripRequest
from src.agents.service import TravelAgentService
from src.repositories.trip_repository import TripRepository


class TripService:
    def __init__(self):
        self.agent_service = TravelAgentService()
        self.repository = TripRepository()

    def discover_spots(self, destination: str, query: str = "tourist attractions"):
        spots = self.agent_service.discover_spots(destination=destination, query=query)
        return [
            {
                "name": spot.get("name"),
                "address": spot.get("address"),
                "rating": spot.get("rating"),
                "reviews": spot.get("reviews"),
                "category": spot.get("category"),
            }
            for spot in (spots or [])
        ]

    @staticmethod
    def _short_id(raw_id: str) -> str:
        if not raw_id:
            return ""
        return raw_id.split("-")[-1] if "-" in raw_id else raw_id

    def _format_itinerary(self, raw: dict) -> dict:
        legs_by_id = {
            leg.get("route_id"): leg
            for leg in raw.get("route_legs", [])
            if leg.get("route_id")
        }

        clean_days = []
        for day_item in raw.get("days", []):
            day_num = day_item.get("day")
            clean_activities = []

            for idx, act in enumerate(day_item.get("activities", []), start=1):
                raw_route_id = act.get("incoming_route_id")
                leg = legs_by_id.get(raw_route_id, {})

                travel_info = None
                if leg:
                    travel_info = {
                        "route_id": f"d{day_num}-r{idx}",
                        "from": leg.get("from"),
                        "distance": leg.get("formatted_distance"),
                        "duration": leg.get("formatted_duration"),
                        "status": leg.get("status", "unverified"),
                    }

                clean_activities.append({
                    "activity_id": f"d{day_num}-a{idx}",
                    "name": act.get("name"),
                    "address": act.get("address"),
                    "rating": act.get("rating"),
                    "start_time": act.get("start_time"),
                    "end_time": act.get("end_time"),
                    "duration_minutes": act.get("duration_minutes"),
                    "travel_from_previous": travel_info,
                    "status": act.get("status", "planned"),
                })

            clean_days.append({
                "day": day_num,
                "date": day_item.get("date"),
                "activities": clean_activities,
            })

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
            "days": clean_days,
            "warnings": raw.get("warnings", []),
        }

    def create_plan(self, request: TripRequest) -> dict:
        itinerary = self.agent_service.plan_trip(request)
        raw_trip_id = itinerary["itinerary_id"]
        short_trip_id = self._short_id(raw_trip_id)
        self.repository.save_trip(raw_trip_id, itinerary)
        return {
            "trip_id": short_trip_id,
            "itinerary": self._format_itinerary(itinerary),
        }

    def cancel_route(self, trip_id: str, route_id: str) -> dict:
        itinerary = self.repository.get_trip(trip_id)
        if itinerary is None:
            raise LookupError("Trip not found")
        updated = self.agent_service.cancel_route(itinerary, route_id)
        storage_id = updated.get("itinerary_id") or trip_id
        self.repository.save_trip(storage_id, updated)
        return {
            "trip_id": self._short_id(storage_id),
            "itinerary": self._format_itinerary(updated),
        }

    def cancel_activity(
        self, trip_id: str, activity_id: str, replacement_query: str | None = None
    ) -> dict:
        itinerary = self.repository.get_trip(trip_id)
        if itinerary is None:
            raise LookupError("Trip not found")
        updated = self.agent_service.cancel_activity(
            itinerary, activity_id, replacement_query
        )
        storage_id = updated.get("itinerary_id") or trip_id
        self.repository.save_trip(storage_id, updated)
        return {
            "trip_id": self._short_id(storage_id),
            "itinerary": self._format_itinerary(updated),
        }

    def extend_trip(self, trip_id: str, new_total_days: int) -> dict:
        itinerary = self.repository.get_trip(trip_id)
        if itinerary is None:
            raise LookupError("Trip not found")
        updated = self.agent_service.extend_trip(itinerary, new_total_days)
        storage_id = updated.get("itinerary_id") or trip_id
        self.repository.save_trip(storage_id, updated)
        return {
            "trip_id": self._short_id(storage_id),
            "itinerary": self._format_itinerary(updated),
        }