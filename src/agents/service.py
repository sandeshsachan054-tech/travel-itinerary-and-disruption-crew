from .serpapi_tools import SerpApiTools
from .planner_agent import PlannerAgent
from .disruption_agent import DisruptionAgent
from .extension_agent import ExtensionAgent


class TravelAgentService:

    def __init__(self):

        # Shared SerpApi tools
        self.tools = SerpApiTools()

        # Initialize all agents
        self.planner = PlannerAgent(
            tools=self.tools
        )

        self.disruption = DisruptionAgent(
            tools=self.tools
        )

        self.extension = ExtensionAgent(
            tools=self.tools,
            planner=self.planner
        )

    # ----------------------------------
    # 1. GENERATE TRAVEL ITINERARY
    # ----------------------------------

    def plan_trip(self, request):

        return self.planner.plan_trip(request)

    # ----------------------------------
    # 2. DISCOVER TOURIST SPOTS
    # ----------------------------------

    def discover_spots(
        self,
        destination,
        query="tourist attractions"
    ):

        return self.tools.search_spots(
            destination,
            query
        )

    # ----------------------------------
    # 3. CANCEL A ROUTE
    # ----------------------------------

    def cancel_route(
        self,
        itinerary,
        route_id
    ):

        return self.disruption.cancel_route(
            itinerary,
            route_id
        )

    # ----------------------------------
    # 4. CANCEL AN ACTIVITY
    # ----------------------------------

    def cancel_activity(
        self,
        itinerary,
        activity_id,
        replacement_query=None
    ):

        return self.disruption.cancel_activity(
            itinerary,
            activity_id,
            replacement_query
        )

    # ----------------------------------
    # 5. EXTEND THE TRIP
    # ----------------------------------

    def extend_trip(
        self,
        itinerary,
        new_total_days
    ):

        return self.extension.extend_trip(
            itinerary,
            new_total_days
        )