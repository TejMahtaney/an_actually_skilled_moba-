"""Coaching input model and conversion to simulation parameters."""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class LaneCoaching(BaseModel):
    approach: str = "standard"          # aggressive | standard | passive
    priority: str = "cs"                # cs | kills | roam
    teamfight_role: str = "damage"      # engage | damage | peel | split


class JungleCoaching(BaseModel):
    pathing: str = "balanced"           # top_focus | bot_focus | balanced | full_farm
    gank_frequency: str = "medium"      # high | medium | low
    objective_focus: str = "medium"     # high | medium | low


class CoachingInput(BaseModel):
    overall_strategy: str = "standard"  # aggressive | standard | scaling | split_push
    win_condition: str = ""
    top_lane: LaneCoaching = Field(default_factory=LaneCoaching)
    bot_lane: LaneCoaching = Field(default_factory=LaneCoaching)
    jungle: JungleCoaching = Field(default_factory=JungleCoaching)
    notes: Optional[str] = None


_APPROACH = {"aggressive": 0.75, "standard": 0.5, "passive": 0.25}
_GANK = {"high": 0.8, "medium": 0.5, "low": 0.25}
_OBJ = {"high": 0.8, "medium": 0.5, "low": 0.3}


def coaching_to_params(c: CoachingInput) -> Dict[str, float]:
    """Deterministic baseline conversion (no LLM)."""
    top_agg = _APPROACH.get(c.top_lane.approach, 0.5)
    bot_agg = _APPROACH.get(c.bot_lane.approach, 0.5)

    if c.jungle.pathing == "top_focus":
        jt, jb = 0.75, 0.25
    elif c.jungle.pathing == "bot_focus":
        jt, jb = 0.25, 0.75
    elif c.jungle.pathing == "full_farm":
        jt, jb = 0.5, 0.5
    else:
        jt, jb = 0.5, 0.5

    teamfight = 0.5
    split = 0.0
    if c.overall_strategy == "aggressive":
        top_agg = max(top_agg, 0.7)
        bot_agg = max(bot_agg, 0.7)
        teamfight = 0.7
    elif c.overall_strategy == "scaling":
        top_agg = min(top_agg, 0.4)
        bot_agg = min(bot_agg, 0.4)
        teamfight = 0.6
    elif c.overall_strategy == "split_push":
        split = 0.8
        teamfight = 0.4

    if c.top_lane.teamfight_role == "split" or c.bot_lane.teamfight_role == "split":
        split = max(split, 0.7)

    obj = _OBJ.get(c.jungle.objective_focus, 0.5)

    # Gank frequency tweaks jungle aggression — bake into focus by skewing
    gank = _GANK.get(c.jungle.gank_frequency, 0.5)
    if gank < 0.4:
        jt = 0.5
        jb = 0.5

    return {
        "top_aggression": round(top_agg, 3),
        "bot_aggression": round(bot_agg, 3),
        "jungle_top_focus": round(jt, 3),
        "jungle_bot_focus": round(jb, 3),
        "teamfight_tendency": round(teamfight, 3),
        "objective_priority": round(obj, 3),
        "split_push_tendency": round(split, 3),
        "gank_frequency": round(gank, 3),
    }


def params_to_sim_params(params: Dict[str, float]) -> Dict[str, object]:
    """Map flat coaching params into the dict shape simulate_match expects."""
    return {
        "aggression": (params.get("top_aggression", 0.5)
                       + params.get("bot_aggression", 0.5)) / 2,
        "objective_priority": params.get("objective_priority", 0.5),
        "gank_frequency": params.get("gank_frequency", 0.5),
        "jungle_focus": {
            "top": params.get("jungle_top_focus", 0.5),
            "bot": params.get("jungle_bot_focus", 0.5),
        },
        "teamfight_tendency": params.get("teamfight_tendency", 0.5),
        "split_push_tendency": params.get("split_push_tendency", 0.0),
        "waveclear": 0.5,
    }
