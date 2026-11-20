from fastapi import HTTPException

from src.agents.schemas import TripRequest
from src.services.trip_service import TripService


class TripController:
    def __init__(self):
        self.service = TripService()

    def get_spots(self, destination: str, query: str = "tourist attractions"):
        try:
            return self.service.discover_spots(destination=destination, query=query)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def create_plan(self, request: TripRequest) -> dict:
        try:
            return self.service.create_plan(request)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def cancel_route(self, trip_id: str, route_id: str) -> dict:
        try:
            return self.service.cancel_route(trip_id, route_id)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def cancel_activity(
        self, trip_id: str, activity_id: str, replacement_query: str | None = None
    ) -> dict:
        try:
            return self.service.cancel_activity(
                trip_id, activity_id, replacement_query
            )
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def extend_trip(self, trip_id: str, new_total_days: int) -> dict:
        try:
            return self.service.extend_trip(trip_id, new_total_days)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        