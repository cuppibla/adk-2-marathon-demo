"""Shared building blocks used by all marathon workflow modes."""
from .schemas import (
    WeatherData,
    CourseData,
    FitnessData,
    RaceStrategy,
    BundledRunData,
    SpecialistInput,
    SpecialistResponse,
)
from .scenarios import SCENARIOS, scenario, slow_mo

__all__ = [
    "WeatherData",
    "CourseData",
    "FitnessData",
    "RaceStrategy",
    "BundledRunData",
    "SpecialistInput",
    "SpecialistResponse",
    "SCENARIOS",
    "scenario",
    "slow_mo",
]
