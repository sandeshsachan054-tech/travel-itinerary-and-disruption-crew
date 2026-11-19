import json
import sqlite3

DB_NAME = "trips.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS trips (trip_id TEXT PRIMARY KEY, itinerary_json TEXT)"
    )
    conn.commit()
    conn.close()


def save_trip(trip_id: str, itinerary: dict):
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        "INSERT OR REPLACE INTO trips (trip_id, itinerary_json) VALUES (?, ?)",
        (trip_id, json.dumps(itinerary, default=str)),
    )
    conn.commit()
    conn.close()


def get_trip(trip_id: str) -> dict | None:
    conn = sqlite3.connect(DB_NAME)
    row = conn.execute(
        "SELECT itinerary_json FROM trips WHERE trip_id = ?",
        (trip_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return json.loads(row[0])
