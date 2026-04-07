"""Pydantic models for moba-coach game data."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AbilityProperties(BaseModel):
    name: str
    ability_type: str          # "active" | "passive" | "ultimate"
    damage_type: str           # "physical" | "magic" | "true" | "none"
    damage_amount: float       # 0.0-1.0 normalised
    cc_type: str               # "none" | "slow" | "root" | "stun" | "knockup" | "charm" | "silence" | "pull"
    cc_duration: float         # 0.0-1.0 normalised
    targeting: str             # "single_target" | "skillshot" | "aoe" | "self" | "ally" | "auto_target"
    range: str                 # "melee" | "short" | "medium" | "long"
    mobility_grant: str        # "none" | "dash" | "blink" | "speed_boost"
    defensive_property: str    # "none" | "shield" | "heal" | "damage_reduction" | "untargetable" | "parry"
    cooldown: str              # "low" | "medium" | "high"
    tags: List[str]
    description: str


class CombatStats(BaseModel):
    attack_damage: float
    magic_damage: float
    durability: float
    mobility: float
    cc: float
    range: float
    burst: float
    sustain_damage: float
    waveclear: float
    utility: float


class TeamContribution(BaseModel):
    engage: float
    peel: float
    frontline: float
    backline_threat: float


class Champion(BaseModel):
    id: str
    name: str
    tag: str
    icon: str
    roles: List[str]
    power_curve: Dict[str, float]
    abilities: List[AbilityProperties]  # exactly 3: two actives + one ultimate
    base_stats: CombatStats
    team_contribution: TeamContribution


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
