
import os
import math
import requests

from dotenv import load_dotenv

load_dotenv()


class SerpApiError(Exception):
    """Custom error for SerpApi operations."""
    pass


class SerpApiTools:

    BASE_URL = "https://serpapi.com/search.json"

    MODES = {
        "driving": "0",
        "two_wheeler": "9",
        "transit": "3",
        "walking": "2",
        "cycling": "1",
    }

    def __init__(self):

        self.api_key = os.getenv("SERPAPI_API_KEY")

        self.session = requests.Session()

    # ==========================================
    # COMMON API REQUEST
    # ==========================================

    def _request(self, params):

        if not self.api_key:
            raise SerpApiError(
                "SERPAPI_API_KEY is missing in .env"
            )

        request_params = {
            **params,
            "api_key": self.api_key
        }

        try:

            response = self.session.get(
                self.BASE_URL,
                params=request_params,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

        except requests.RequestException as error:

            raise SerpApiError(
                f"SerpApi request failed: {error}"
            ) from error

        if data.get("error"):

            raise SerpApiError(
                data["error"]
            )

        return data

    # ==========================================
    # SEARCH TOURIST SPOTS
    # ==========================================

    def search_spots(
        self,
        destination,
        query="tourist attractions",
        limit=10
    ):

        params = {

            "engine": "google_maps",

            "type": "search",

            "q": f"{query} in {destination}",

            "hl": "en",

            "gl": "in"

        }

        data = self._request(params)

        results = []

        for place in data.get("local_results", [])[:limit]:

            coordinates = (
                place.get("gps_coordinates") or {}
            )

            results.append({

                "name": place.get("title"),

                "address": place.get("address"),

                "rating": place.get("rating"),

                "reviews": place.get("reviews"),

                "category": query,

                "place_id": place.get("place_id"),

                "data_id": place.get("data_id"),

                "latitude": coordinates.get("latitude"),

                "longitude": coordinates.get("longitude"),

                "source": "SerpApi Google Maps"

            })

        return results

    # ==========================================
    # GOOGLE MAPS DIRECTIONS
    # ==========================================

    def get_route(
        self,
        origin,
        destination,
        travel_mode="driving",
        origin_data_id=None,
        destination_data_id=None,
        origin_coords=None,
        destination_coords=None
    ):

        if travel_mode not in self.MODES:

            raise ValueError(
                f"Unsupported travel mode: {travel_mode}"
            )

        params = {

            "engine": "google_maps_directions",

            "travel_mode": self.MODES[travel_mode],

            "hl": "en",

            "gl": "in"

        }

        # Origin identification
        if origin_data_id:

            params["start_data_id"] = origin_data_id

        elif origin_coords:

            params["start_coords"] = origin_coords

        else:

            params["start_addr"] = origin

        # Destination identification
        if destination_data_id:

            params["end_data_id"] = destination_data_id

        elif destination_coords:

            params["end_coords"] = destination_coords

        else:

            params["end_addr"] = destination

        data = self._request(params)

        directions = data.get("directions") or []

        if not directions:

            raise SerpApiError(
                f"No route found between {origin} and {destination}"
            )

        route = directions[0]

        duration_seconds = route.get("duration")

        duration_minutes = None

        if duration_seconds is not None:

            duration_minutes = math.ceil(
                float(duration_seconds) / 60
            )

        # Fare is optional. Never invent prices.
        fare = (
            route.get("fare")
            or route.get("transit_fare")
        )

        cost_amount = None
        currency = None

        if isinstance(fare, dict):

            cost_amount = (
                fare.get("amount")
                or fare.get("value")
            )

            currency = (
                fare.get("currency")
                or fare.get("currency_code")
            )

        elif isinstance(fare, (int, float)):

            cost_amount = fare

        return {

            "origin": origin,

            "destination": destination,

            "travel_mode": travel_mode,

            "distance_meters": route.get("distance"),

            "duration_seconds": duration_seconds,

            "duration_minutes": duration_minutes,

            "formatted_distance": route.get(
                "formatted_distance"
            ),

            "formatted_duration": route.get(
                "formatted_duration"
            ),

            "cost_amount": cost_amount,

            "currency": currency,

            "source": "SerpApi Google Maps Directions"

        }
