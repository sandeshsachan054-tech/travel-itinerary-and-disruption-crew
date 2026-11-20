from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.schemas import TripRequest
from src.controllers.trip_controller import TripController

router = APIRouter()
controller = TripController()


class CancelRouteInput(BaseModel):
    trip_id: str
    route_id: str


class CancelActivityInput(BaseModel):
    trip_id: str
    activity_id: str
    replacement_query: str | None = None


class ExtendTripInput(BaseModel):
    trip_id: str
    new_total_days: int


@router.get("/spots")
def spots(destination: str, query: str = "tourist attractions"):
    return controller.get_spots(destination=destination, query=query)


@router.post("/plan")
def create_plan(request: TripRequest):
    return controller.create_plan(request)


@router.post("/cancel-route")
def cancel_route(data: CancelRouteInput):
    return controller.cancel_route(data.trip_id, data.route_id)


@router.post("/cancel-activity")
def cancel_activity(data: CancelActivityInput):
    return controller.cancel_activity(
        data.trip_id, data.activity_id, data.replacement_query
    )


@router.post("/extend-trip")
def extend_trip(data: ExtendTripInput):
    return controller.extend_trip(data.trip_id, data.new_total_days)
