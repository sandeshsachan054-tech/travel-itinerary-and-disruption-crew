import json
import sqlite3


class TripRepository:
    def __init__(self, db_name: str = "trips.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self) -> None:
        conn = sqlite3.connect(self.db_name)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS trips (trip_id TEXT PRIMARY KEY, itinerary_json TEXT)"
        )
        conn.commit()
        conn.close()

    def save_trip(self, trip_id: str, itinerary: dict) -> None:
        conn = sqlite3.connect(self.db_name)
        conn.execute(
            "INSERT OR REPLACE INTO trips (trip_id, itinerary_json) VALUES (?, ?)",
            (trip_id, json.dumps(itinerary, default=str)),
        )
        conn.commit()
        conn.close()

    def get_trip(self, trip_id: str) -> dict | None:
        conn = sqlite3.connect(self.db_name)
        row = conn.execute(
            "SELECT itinerary_json FROM trips WHERE trip_id = ?",
            (trip_id,),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return json.loads(row[0])