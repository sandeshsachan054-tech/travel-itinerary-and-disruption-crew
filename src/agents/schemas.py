from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TripRequest(BaseModel):

    destination: str = Field(min_length=2)

    days: int = Field(default=3, ge=1, le=14)

    start_date: date | None = None

    start_location: str | None = None

    interests: list[str] = Field(
        default_factory=lambda: ["tourist attractions"]
    )

    selected_spots: list[str] = Field(default_factory=list)

    daily_start_time: str = "09:00"

    daily_end_time: str = "20:00"

    visit_duration_minutes: int = Field(
        default=90,
        ge=15,
        le=360
    )

    travel_mode: Literal[
        "driving",
        "transit",
        "walking",
        "cycling",
        "two_wheeler"
    ] = "driving"

    currency: str = "INR"

    budget: float | None = None

    @field_validator("daily_start_time", "daily_end_time")
    @classmethod
    def validate_time(cls, value):
        datetime.strptime(value, "%H:%M")
        return value

    model_config = {
        "extra": "ignore"
    }