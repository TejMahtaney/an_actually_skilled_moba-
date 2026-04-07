"""Pydantic models for moba-coach game data."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Champion(BaseModel):
    id: str
    name: str
    tag: str
    icon: str
    roles: List[str]
    power_curve: Dict[str, float]
    description: str


class MatchResult(BaseModel):
    winner: str  # "blue" or "red"
    duration_minutes: float
    blue_team: List[str]
    red_team: List[str]
    notes: Optional[str] = None


class DraftState(BaseModel):
    blue_picks: List[str] = Field(default_factory=list)
    red_picks: List[str] = Field(default_factory=list)
    blue_bans: List[str] = Field(default_factory=list)
    red_bans: List[str] = Field(default_factory=list)
    turn: str = "blue"  # whose turn it is to pick


class CoachingInput(BaseModel):
    draft: DraftState
    player_team: str = "blue"
    player_role: Optional[str] = None
    question: Optional[str] = None


class SimulationParams(BaseModel):
    blue_team: List[str]
    red_team: List[str]
    iterations: int = 1000
    seed: Optional[int] = None
