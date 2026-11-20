from src.agents.schemas import TripRequest
from src.agents.service import TravelAgentService
from src.repositories.trip_repository import TripRepository


class TripService:
    def __init__(self):
        self.agent_service = TravelAgentService()
        self.repository = TripRepository()

    def discover_spots(self, destination: str, query: str = "tourist attractions"):
        return self.agent_service.discover_spots(destination=destination, query=query)

    def create_plan(self, request: TripRequest) -> dict:
        itinerary = self.agent_service.plan_trip(request)
        trip_id = itinerary["itinerary_id"]
        self.repository.save_trip(trip_id, itinerary)
        return {"trip_id": trip_id, "itinerary": itinerary}

    def cancel_route(self, trip_id: str, route_id: str) -> dict:
        itinerary = self.repository.get_trip(trip_id)
        if itinerary is None:
            raise LookupError("Trip not found")
        updated = self.agent_service.cancel_route(itinerary, route_id)
        self.repository.save_trip(trip_id, updated)
        return {"trip_id": trip_id, "itinerary": updated}

    def cancel_activity(
        self, trip_id: str, activity_id: str, replacement_query: str | None = None
    ) -> dict:
        itinerary = self.repository.get_trip(trip_id)
        if itinerary is None:
            raise LookupError("Trip not found")
        updated = self.agent_service.cancel_activity(
            itinerary, activity_id, replacement_query
        )
        self.repository.save_trip(trip_id, updated)
        return {"trip_id": trip_id, "itinerary": updated}

    def extend_trip(self, trip_id: str, new_total_days: int) -> dict:
        itinerary = self.repository.get_trip(trip_id)
        if itinerary is None:
            raise LookupError("Trip not found")
        updated = self.agent_service.extend_trip(itinerary, new_total_days)
        self.repository.save_trip(trip_id, updated)
        return {"trip_id": trip_id, "itinerary": updated}
    