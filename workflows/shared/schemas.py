"""Pydantic schemas that flow between nodes in marathon workflows."""
from __future__ import annotations

from pydantic import BaseModel, Field


class WeatherData(BaseModel):
    temp_f: float
    wind_mph: float
    wind_direction: str
    humidity_pct: int
    conditions: str


class CourseData(BaseModel):
    name: str
    distance_mi: float
    total_elevation_gain_ft: int
    hardest_mile: int
    hardest_mile_grade_pct: float


class FitnessData(BaseModel):
    avg_pace_per_mile_sec: int
    longest_recent_run_mi: float
    weekly_mileage_mi: int


class RaceStrategy(BaseModel):
    target_finish: str = Field(
        description="Clean finish time only, format H:MM:SS. Example: '3:30:00'. "
        "Do NOT include explanations, parentheticals, or extra commentary."
    )
    pacing_advice: str = Field(description="One concise sentence about race pacing strategy.")
    fueling_plan: str = Field(description="One concise sentence about hydration and nutrition.")
    gear: str = Field(description="One concise sentence about clothing and equipment.")
    key_warning: str = Field(description="One concise sentence flagging the biggest risk for this race.")


class BundledRunData(BaseModel):
    """Shape of the JoinNode payload — keys match the upstream function names."""
    fetch_weather: WeatherData
    analyze_course: CourseData
    pull_fitness: FitnessData
