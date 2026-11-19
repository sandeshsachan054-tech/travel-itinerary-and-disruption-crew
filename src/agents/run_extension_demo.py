
from pprint import pprint

from src.agents import TravelAgentService


def main():

    print("\n========== TRIP EXTENSION TEST ==========\n")

    service = TravelAgentService()

    # First generate a 3-day trip
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

    print("Generating original 3-day trip...")

    itinerary = service.plan_trip(request)

    print("\nOriginal trip days:")
    print(len(itinerary["days"]))

    # Extend 3-day trip to 7 days
    print("\nExtending trip from 3 days to 7 days...")

    try:

        extended = service.extend_trip(
            itinerary,
            new_total_days=7
        )

        print("\n========== EXTENSION RESULT ==========\n")

        print("Destination:", extended["destination"])

        print("Total days:", len(extended["days"]))

        print("\nExtension details:")

        pprint(
            extended.get("trip_extension"),
            sort_dicts=False
        )

        print("\n========== NEW DAYS GENERATED ==========\n")

        for day in extended["days"]:

            print(
                f"\nDay {day['day']} - {day['date']}"
            )

            for activity in day["activities"]:

                print(
                    "Activity:",
                    activity["name"]
                )

                print(
                    "Time:",
                    activity["start_time"],
                    "-",
                    activity["end_time"]
                )

        print("\n========== EXTENSION TEST COMPLETED ==========")

    except Exception as error:

        print("\nEXTENSION ERROR:")
        print(error)


if __name__ == "__main__":

    main()
