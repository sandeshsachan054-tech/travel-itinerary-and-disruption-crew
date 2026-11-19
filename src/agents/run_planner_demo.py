
from pprint import pprint

from src.agents import TravelAgentService


def main():

    print("\n========== INITIALIZING AGENTS ==========\n")

    # Initialize agent service
    service = TravelAgentService()

    # Trip request
    request = {

        "destination": "Jaipur",

        "days": 3,

        "start_date": "2026-12-01",

        "start_location": "Jaipur Railway Station",

        "interests": [
            "heritage forts",
            "restaurants",
            "tourist attractions"
        ],

        "travel_mode": "driving",

        "visit_duration_minutes": 90

    }

    # =====================================
    # PLANNER AGENT TEST
    # =====================================

    print("\n========== PLANNER AGENT TEST ==========\n")

    result = service.plan_trip(request)

    print("\n========== GENERATED ITINERARY ==========\n")

    pprint(result, sort_dicts=False)

    # =====================================
    # DISRUPTION AGENT TEST
    # =====================================

    print("\n========== DISRUPTION AGENT TEST ==========\n")

    if result.get("route_legs"):

        route_id = result["route_legs"][0]["route_id"]

        print("Cancelling route:", route_id)

        try:

            updated = service.cancel_route(
                result,
                route_id
            )

            print("\n========== DISRUPTION RESULT ==========\n")

            pprint(
                updated.get("last_disruption"),
                sort_dicts=False
            )

            print("\n========== UPDATED ROUTE ==========\n")

            pprint(
                [
                    route
                    for route in updated["route_legs"]
                    if route["route_id"] == route_id
                ],
                sort_dicts=False
            )

            print("\n========== UPDATED ITINERARY ==========\n")

            pprint(updated, sort_dicts=False)

        except Exception as error:

            print("\nDISRUPTION ERROR:")
            print(error)

    else:

        print("No routes available for cancellation testing.")

    print("\n========== ALL TESTS FINISHED ==========\n")


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print("\nPROGRAM ERROR:")
        print(error)
