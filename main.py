from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_trip, init_db, save_trip
from src.agents.schemas import TripRequest
from src.agents.service import TravelAgentService

load_dotenv()
init_db()

app = FastAPI(title="Travel Crew API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

service = TravelAgentService()


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


@app.get("/spots")
def spots(destination: str, query: str = "tourist attractions"):
    try:
        return service.discover_spots(destination=destination, query=query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plan")
def create_plan(request: TripRequest):
    try:
        itinerary = service.plan_trip(request)
        trip_id = itinerary["itinerary_id"]
        save_trip(trip_id, itinerary)
        return {"trip_id": trip_id, "itinerary": itinerary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cancel-route")
def cancel_route(data: CancelRouteInput):
    itinerary = get_trip(data.trip_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        updated = service.cancel_route(itinerary, data.route_id)
        save_trip(data.trip_id, updated)
        return {"trip_id": data.trip_id, "itinerary": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cancel-activity")
def cancel_activity(data: CancelActivityInput):
    itinerary = get_trip(data.trip_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        updated = service.cancel_activity(
            itinerary, data.activity_id, data.replacement_query
        )
        save_trip(data.trip_id, updated)
        return {"trip_id": data.trip_id, "itinerary": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extend-trip")
def extend_trip(data: ExtendTripInput):
    itinerary = get_trip(data.trip_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        updated = service.extend_trip(itinerary, data.new_total_days)
        save_trip(data.trip_id, updated)
        return {"trip_id": data.trip_id, "itinerary": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    