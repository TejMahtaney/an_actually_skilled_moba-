"""Phase-based deterministic match simulation with random variance.

No LLM is used here — pure maths. The simulation runs three phases
(early/mid/late) and produces a full MatchResult.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

try:
    from .champions import CHAMPIONS
    from .matchups import get_matchup, get_synergy
    from .models import MatchResult
except ImportError:
    from champions import CHAMPIONS
    from matchups import get_matchup, get_synergy
    from models import MatchResult


# ---------------------------------------------------------------------------
# Defaults & helpers
# ---------------------------------------------------------------------------

DEFAULT_PARAMS = {
    "aggression": 0.5,        # 0-1, how aggressive players play
    "objective_priority": 0.5,  # 0-1, weight on objectives vs farm
    "gank_frequency": 0.5,    # 0-1, jungler gank rate
    "jungle_focus": {"top": 0.5, "bot": 0.5},  # gank weighting
    "teamfight_tendency": 0.5,  # 0-1
    "split_push_tendency": 0.0,  # 0-1
    "waveclear": 0.5,         # 0-1
    "ward_awareness": 0.4,    # fixed-ish, used by enemy gank check
}

# Per-champion gank ratings (rough scale 0-1)
GANK_RATING = {
    "fang": 0.9, "shade": 0.8, "siren": 0.75, "ironclad": 0.6,
    "warden": 0.55, "reaver": 0.5, "rapier": 0.45, "sage": 0.4,
    "whisper": 0.3, "solara": 0.45,
}


def _merge_params(p: Optional[dict]) -> dict:
    out = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_PARAMS.items()}
    if p:
        for k, v in p.items():
            out[k] = v
    return out


def _team_by_role(team: List[dict]) -> Dict[str, dict]:
    return {p["role"]: p for p in team}


def _power(champ_id: str, phase: str) -> float:
    return CHAMPIONS[champ_id].power_curve[phase]


def _team_synergy(team: List[dict]) -> int:
    ids = [p["champion_id"] for p in team]
    total = 0
    pairs = 0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            total += get_synergy(ids[i], ids[j])
            pairs += 1
    return total // max(pairs, 1)


# ---------------------------------------------------------------------------
# State container
# ---------------------------------------------------------------------------

class _PlayerState:
    def __init__(self, champion_id: str, role: str):
        self.champion_id = champion_id
        self.role = role
        self.kills = 0
        self.deaths = 0
        self.assists = 0
        self.cs = 0
        self.gold = 500  # starting gold

    def to_dict(self) -> dict:
        return {
            "champion_id": self.champion_id,
            "role": self.role,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "cs": self.cs,
        }


# ---------------------------------------------------------------------------
# Phase 1 — early game
# ---------------------------------------------------------------------------

def _resolve_lane(blue: _PlayerState, red: _PlayerState,
                  bp: dict, rp: dict, rng: random.Random,
                  events: list) -> None:
    base = get_matchup(blue.champion_id, red.champion_id)  # blue perspective

    bagg = bp["aggression"]
    ragg = rp["aggression"]

    if bagg > 0.6 and base > 50:
        base += 3
    elif bagg > 0.6 and base < 50:
        base -= 5
    elif bagg < 0.4 and base < 50:
        base += 2

    if ragg > 0.6 and base < 50:
        base -= 3
    elif ragg > 0.6 and base > 50:
        base += 5
    elif ragg < 0.4 and base > 50:
        base -= 2

    base += rng.uniform(-8, 8)

    # Map result to CS / gold / kills.
    diff = base - 50  # >0 favours blue
    blue.cs += int(80 + diff)
    red.cs += int(80 - diff)
    blue.gold += int(80 + diff) * 14 + max(0, int(diff * 5))
    red.gold += int(80 - diff) * 14 + max(0, int(-diff * 5))

    # Solo kill chance
    if abs(diff) > 12 and rng.random() < 0.55:
        if diff > 0:
            blue.kills += 1
            red.deaths += 1
            blue.gold += 300
            events.append({"time": rng.randint(3, 9),
                           "event": f"solo kill {blue.role}",
                           "details": f"{blue.champion_id} killed {red.champion_id}"})
        else:
            red.kills += 1
            blue.deaths += 1
            red.gold += 300
            events.append({"time": rng.randint(3, 9),
                           "event": f"solo kill {red.role}",
                           "details": f"{red.champion_id} killed {blue.champion_id}"})

    # Tower plate gold
    if diff > 5:
        blue.gold += 160
    elif diff < -5:
        red.gold += 160


def _resolve_jungle(blue_state: Dict[str, _PlayerState],
                    red_state: Dict[str, _PlayerState],
                    bp: dict, rp: dict, rng: random.Random,
                    events: list) -> None:
    bj = blue_state["jungle"]
    rj = red_state["jungle"]
    base = get_matchup(bj.champion_id, rj.champion_id)
    base += rng.uniform(-6, 6)

    # Farm always
    bj.cs += 60
    rj.cs += 60
    bj.gold += 900
    rj.gold += 900

    if base > 50:
        bj.gold += int((base - 50) * 20)
    else:
        rj.gold += int((50 - base) * 20)

    # Ganks
    for jstate, params, allies, enemies, side in (
        (bj, bp, blue_state, red_state, "blue"),
        (rj, rp, red_state, blue_state, "red"),
    ):
        attempts = int(round(params["gank_frequency"] * 4))  # 0-4
        focus = params["jungle_focus"]
        for _ in range(attempts):
            lane = "top" if rng.random() < focus.get("top", 0.5) else "bot"
            gank_rating = GANK_RATING.get(jstate.champion_id, 0.5)
            success_p = (params["gank_frequency"] * 0.4 +
                         gank_rating * 0.6) * (1 - 0.4)
            if rng.random() < success_p:
                ally = allies[lane]
                enemy = enemies[lane]
                ally.kills += 1
                jstate.assists += 1
                enemy.deaths += 1
                ally.gold += 280
                jstate.gold += 150
                events.append({
                    "time": rng.randint(4, 10),
                    "event": f"{side} gank {lane}",
                    "details": f"{jstate.champion_id} ganked for {ally.champion_id}",
                })


def _phase_one(blue_state, red_state, bp, rp, rng, events, timeline):
    _resolve_lane(blue_state["top"], red_state["top"], bp, rp, rng, events)
    _resolve_lane(blue_state["bot"], red_state["bot"], bp, rp, rng, events)
    _resolve_jungle(blue_state, red_state, bp, rp, rng, events)

    bg = sum(p.gold for p in blue_state.values())
    rg = sum(p.gold for p in red_state.values())
    timeline.append((10, bg - rg))


# ---------------------------------------------------------------------------
# Phase 2 — mid game
# ---------------------------------------------------------------------------

def _phase_two(blue_state, red_state, bp, rp, rng, events, timeline) -> dict:
    bg = sum(p.gold for p in blue_state.values())
    rg = sum(p.gold for p in red_state.values())
    gold_lead = bg - rg

    # Wyrm contest at minute 12
    bj_power = _power(blue_state["jungle"].champion_id, "mid")
    rj_power = _power(red_state["jungle"].champion_id, "mid")
    blue_wyrm_score = 0.6 * bj_power + 0.4 * bp["objective_priority"] + gold_lead / 20000
    red_wyrm_score = 0.6 * rj_power + 0.4 * rp["objective_priority"] - gold_lead / 20000
    blue_wyrm_score += rng.uniform(-0.1, 0.1)
    red_wyrm_score += rng.uniform(-0.1, 0.1)

    if blue_wyrm_score >= red_wyrm_score:
        wyrm_by = "blue"
        blue_buff = 1.08
        red_buff = 1.0
        for p in blue_state.values():
            p.gold += 120
    else:
        wyrm_by = "red"
        blue_buff = 1.0
        red_buff = 1.08
        for p in red_state.values():
            p.gold += 120
    events.append({"time": 12, "event": "Rift Wyrm",
                   "details": f"{wyrm_by} team secured the wyrm"})

    # Skirmishes
    n_skirms = rng.randint(1, 3)
    blue_wins = 0
    red_wins = 0
    for i in range(n_skirms):
        b_strength = sum(_power(p.champion_id, "mid") * (1 + p.gold / 8000)
                         for p in blue_state.values()) * blue_buff
        r_strength = sum(_power(p.champion_id, "mid") * (1 + p.gold / 8000)
                         for p in red_state.values()) * red_buff
        b_strength += _team_synergy(
            [{"champion_id": p.champion_id} for p in blue_state.values()]) * 0.05
        r_strength += _team_synergy(
            [{"champion_id": p.champion_id} for p in red_state.values()]) * 0.05
        b_strength *= rng.uniform(0.9, 1.1)
        r_strength *= rng.uniform(0.9, 1.1)
        t = 14 + i * 3
        if b_strength > r_strength:
            blue_wins += 1
            for p in blue_state.values():
                p.kills += 1
                p.gold += 220
            for p in red_state.values():
                p.deaths += 1
            events.append({"time": t, "event": "skirmish",
                           "details": "blue won a skirmish"})
        else:
            red_wins += 1
            for p in red_state.values():
                p.kills += 1
                p.gold += 220
            for p in blue_state.values():
                p.deaths += 1
            events.append({"time": t, "event": "skirmish",
                           "details": "red won a skirmish"})

    # Tower siege based on gold lead and waveclear
    bg = sum(p.gold for p in blue_state.values())
    rg = sum(p.gold for p in red_state.values())
    towers = {"blue": 0, "red": 0}
    for _ in range(2):
        if bg > rg:
            chance = 0.6 + bp["waveclear"] * 0.15
            if rng.random() < chance:
                towers["blue"] += 1
                for p in blue_state.values():
                    p.gold += 125
        else:
            chance = 0.6 + rp["waveclear"] * 0.15
            if rng.random() < chance:
                towers["red"] += 1
                for p in red_state.values():
                    p.gold += 125
        bg = sum(p.gold for p in blue_state.values())
        rg = sum(p.gold for p in red_state.values())

    timeline.append((22, bg - rg))
    return {"wyrm_by": wyrm_by, "towers": towers,
            "skirmish_score": (blue_wins, red_wins)}


# ---------------------------------------------------------------------------
# Phase 3 — late game
# ---------------------------------------------------------------------------

def _phase_three(blue_state, red_state, bp, rp, rng, events, timeline,
                 mid_info) -> Tuple[str, int, dict]:
    towers = mid_info["towers"]
    blue_split = max((bp["split_push_tendency"] for _ in [0]), default=0)
    red_split = max((rp["split_push_tendency"] for _ in [0]), default=0)

    blue_wins = 0
    red_wins = 0
    minute = 24

    def team_strength(state, params):
        s = sum(_power(p.champion_id, "late") *
                (1 + p.gold / 9000) *
                (0.7 + 0.6 * params["teamfight_tendency"])
                for p in state.values())
        s += _team_synergy(
            [{"champion_id": p.champion_id} for p in state.values()]) * 0.08
        return s * rng.uniform(0.92, 1.08)

    winner = None
    for fight_idx in range(3):
        bs = team_strength(blue_state, bp)
        rs = team_strength(red_state, rp)
        if bs > rs:
            blue_wins += 1
            for p in blue_state.values():
                p.kills += 2
                p.gold += 350
            for p in red_state.values():
                p.deaths += 1
            events.append({"time": minute, "event": "teamfight",
                           "details": "blue won a teamfight"})
        else:
            red_wins += 1
            for p in red_state.values():
                p.kills += 2
                p.gold += 350
            for p in blue_state.values():
                p.deaths += 1
            events.append({"time": minute, "event": "teamfight",
                           "details": "red won a teamfight"})

        bg = sum(p.gold for p in blue_state.values())
        rg = sum(p.gold for p in red_state.values())
        timeline.append((minute, bg - rg))
        minute += 4

        # Split push win condition
        if blue_split > 0.7 and bg > rg and rng.random() < 0.4:
            winner = "blue"
            events.append({"time": minute, "event": "split push",
                           "details": "blue completed a split push"})
            towers["blue"] += 2
            break
        if red_split > 0.7 and rg > bg and rng.random() < 0.4:
            winner = "red"
            events.append({"time": minute, "event": "split push",
                           "details": "red completed a split push"})
            towers["red"] += 2
            break

        if blue_wins >= 2:
            winner = "blue"
            break
        if red_wins >= 2:
            winner = "red"
            break

        # Losing team can force another fight if gold diff < 3000
        if abs(bg - rg) >= 3000:
            winner = "blue" if bg > rg else "red"
            break

    if winner is None:
        bg = sum(p.gold for p in blue_state.values())
        rg = sum(p.gold for p in red_state.values())
        winner = "blue" if bg >= rg else "red"

    if winner == "blue":
        towers["blue"] += 2
    else:
        towers["red"] += 2

    events.append({"time": minute, "event": "nexus",
                   "details": f"{winner} destroyed the nexus"})
    return winner, minute, towers


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def simulate_match(
    blue_team: List[dict],
    red_team: List[dict],
    blue_params: Optional[dict] = None,
    red_params: Optional[dict] = None,
    seed: Optional[int] = None,
) -> MatchResult:
    rng = random.Random(seed)
    bp = _merge_params(blue_params)
    rp = _merge_params(red_params)

    blue_state = {p["role"]: _PlayerState(p["champion_id"], p["role"])
                  for p in blue_team}
    red_state = {p["role"]: _PlayerState(p["champion_id"], p["role"])
                 for p in red_team}

    events: list = []
    timeline: List[Tuple[int, int]] = [(0, 0)]

    _phase_one(blue_state, red_state, bp, rp, rng, events, timeline)
    mid_info = _phase_two(blue_state, red_state, bp, rp, rng, events, timeline)
    winner, duration, towers = _phase_three(
        blue_state, red_state, bp, rp, rng, events, timeline, mid_info)

    # Assists: rough — every kill on a team gives an assist to one ally
    for state in (blue_state, red_state):
        ids = list(state.values())
        for i, p in enumerate(ids):
            p.assists = sum(q.kills for q in ids if q is not p) // 2

    blue_kills = sum(p.kills for p in blue_state.values())
    red_kills = sum(p.kills for p in red_state.values())

    performances = [p.to_dict() for p in blue_state.values()] + \
                   [p.to_dict() for p in red_state.values()]

    def _score(perf):
        return perf["kills"] * 3 + perf["assists"] - perf["deaths"] * 2 + perf["cs"] * 0.02

    mvp = max(performances, key=_score)["champion_id"]

    result = MatchResult(
        winner=winner,
        duration_minutes=float(duration),
        blue_team=[p["champion_id"] for p in blue_team],
        red_team=[p["champion_id"] for p in red_team],
        notes=(
            f"kills {blue_kills}-{red_kills}; "
            f"towers B{towers['blue']}/R{towers['red']}; "
            f"wyrm:{mid_info['wyrm_by']}; mvp:{mvp}"
        ),
    )
    # Attach extended data as attributes for callers that want it
    result.__dict__["blue_kills"] = blue_kills
    result.__dict__["red_kills"] = red_kills
    result.__dict__["gold_diff_timeline"] = timeline
    result.__dict__["towers_destroyed"] = towers
    result.__dict__["wyrm_secured_by"] = mid_info["wyrm_by"]
    result.__dict__["key_events"] = events
    result.__dict__["player_performances"] = performances
    result.__dict__["mvp"] = mvp
    return result


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    blue = [
        {"champion_id": "ironclad", "role": "top"},
        {"champion_id": "solara", "role": "bot"},
        {"champion_id": "fang", "role": "jungle"},
    ]
    red = [
        {"champion_id": "reaver", "role": "top"},
        {"champion_id": "whisper", "role": "bot"},
        {"champion_id": "warden", "role": "jungle"},
    ]
    result = simulate_match(blue, red, seed=42)
    print(f"Winner: {result.winner}  ({int(result.duration_minutes)} min)")
    print(f"Score:  {result.__dict__['blue_kills']} - {result.__dict__['red_kills']}")
    print(f"Towers: {result.__dict__['towers_destroyed']}")
    print(f"Wyrm:   {result.__dict__['wyrm_secured_by']}")
    print(f"MVP:    {result.__dict__['mvp']}")
    print("Gold diff timeline:")
    for t, g in result.__dict__["gold_diff_timeline"]:
        print(f"  min {t:>2}: {g:+d}")
    print("Key events:")
    for e in result.__dict__["key_events"]:
        print(f"  [{e['time']:>2}'] {e['event']}: {e['details']}")
    print("Performances:")
    for p in result.__dict__["player_performances"]:
        print(f"  {p['champion_id']:>9} ({p['role']:>6}): "
              f"{p['kills']}/{p['deaths']}/{p['assists']}  cs={p['cs']}")
