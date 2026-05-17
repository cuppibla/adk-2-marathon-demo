"""Shared building blocks used by all marathon workflow modes."""
from .schemas import (
    WeatherData,
    CourseData,
    FitnessData,
    RaceStrategy,
    BundledRunData,
    SpecialistInput,
    SpecialistResponse,
    DecomposerOutput,
    ResearchFinding,
    DeepResearchBriefing,
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
    "DecomposerOutput",
    "ResearchFinding",
    "DeepResearchBriefing",
    "SCENARIOS",
    "scenario",
    "slow_mo",
]
