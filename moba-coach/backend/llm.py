"""LLM integration layer — talks to a local Ollama instance.

Every method has a deterministic fallback so the game is playable even
if Ollama is unreachable.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from typing import Any, Dict, List, Optional

import httpx

try:
    from .champions import CHAMPIONS
    from .config import OLLAMA_BASE_URL, OLLAMA_MODEL
    from .matchups import get_matchup, get_synergy
    from .stats_engine import compute_combat_stats, compute_team_contribution
except ImportError:
    from champions import CHAMPIONS
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL
    from matchups import get_matchup, get_synergy
    from stats_engine import compute_combat_stats, compute_team_contribution


log = logging.getLogger("moba-coach.llm")

# Toggle prompt/response logging by setting MOBACOACH_LOG_LLM=1
LOG_PROMPTS = os.environ.get("MOBACOACH_LOG_LLM", "") in ("1", "true", "yes")
# Force fallback-only mode (no network calls)
NO_LLM = os.environ.get("MOBACOACH_NO_LLM", "") in ("1", "true", "yes")

DEFAULT_PARAMS = {
    "top_aggression": 0.5,
    "bot_aggression": 0.5,
    "jungle_top_focus": 0.5,
    "jungle_bot_focus": 0.5,
    "teamfight_tendency": 0.5,
    "objective_priority": 0.5,
    "split_push_tendency": 0.5,
}

ARCHETYPE_BAN_NOTE = {
    "Aggressor": "You favour banning scaling/late-game champions that survive your tempo.",
    "Turtle": "You favour banning early-game lane bullies and high-pressure junglers.",
    "Strategist": "You favour banning champions with disruptive teamfight ultimates.",
    "Default": "You ban the most generally threatening champion in the pool.",
}


def _champ_blurb(cid: str) -> str:
    c = CHAMPIONS[cid]
    actives = [a for a in c.abilities if a.ability_type != "ultimate"]
    ult = next((a for a in c.abilities if a.ability_type == "ultimate"), None)
    ability_line = ", ".join(a.name for a in actives)
    ult_line = ult.name if ult else "-"

    stats = compute_combat_stats(cid)
    tc = compute_team_contribution(cid)
    combined = {**stats, **tc}
    ordered = sorted(combined.items(), key=lambda kv: kv[1], reverse=True)
    strong = ", ".join(f"{k}({v:.2f})" for k, v in ordered[:3])
    weak = ", ".join(f"{k}({v:.2f})" for k, v in ordered[-2:])

    return (
        f"- {c.id}: {c.name} ({c.tag}, roles={'/'.join(c.roles)}) "
        f"| Abilities: {ability_line} | Ult: {ult_line} "
        f"| Strong: {strong} | Weak: {weak}"
    )


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort JSON extraction from a model response."""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def _clamp01(x: Any) -> float:
    try:
        v = float(x)
    except Exception:
        return 0.5
    return max(0.0, min(1.0, v))


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    # ----- core -----------------------------------------------------------
    async def generate(self, system_prompt: str, user_prompt: str,
                       json_mode: bool = False) -> str:
        if NO_LLM:
            return "__LLM_UNAVAILABLE__"
        payload: Dict[str, Any] = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        if LOG_PROMPTS:
            print("\n--- LLM REQUEST ---")
            print(f"system: {system_prompt[:300]}{'...' if len(system_prompt) > 300 else ''}")
            print(f"user:   {user_prompt[:600]}{'...' if len(user_prompt) > 600 else ''}")
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                r = await client.post(f"{self.base_url}/api/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                resp = data.get("response", "")
                if LOG_PROMPTS:
                    print(f"--- LLM RESPONSE ---\n{resp[:600]}{'...' if len(resp) > 600 else ''}\n")
                return resp
        except Exception as e:
            log.error("Ollama generate failed: %r", e)
            return "__LLM_UNAVAILABLE__"

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    # ----- enemy ban ------------------------------------------------------
    async def enemy_ban(self, available_champions: List[str],
                        coach_archetype: str) -> str:
        if not available_champions:
            return ""
        system = (
            f"You are an AI coach for a 3v3 MOBA called MOBA Coach. "
            f"Your coaching style is: {coach_archetype}. You are deciding which "
            f"champion to ban. You must respond with ONLY valid JSON, no other "
            f"text. Format: {{\"ban\": \"champion_id\", \"reasoning\": \"one sentence\"}}"
        )
        note = ARCHETYPE_BAN_NOTE.get(coach_archetype, ARCHETYPE_BAN_NOTE["Default"])
        user = (
            f"Banning tendency: {note}\n\n"
            f"Available champions:\n"
            + "\n".join(_champ_blurb(c) for c in available_champions)
            + "\n\nRespond with valid JSON only."
        )
        text = await self.generate(system, user, json_mode=True)
        data = _extract_json(text)
        if data and data.get("ban") in available_champions:
            return data["ban"]
        return self._fallback_ban(available_champions, coach_archetype)

    def _fallback_ban(self, available: List[str], archetype: str) -> str:
        if archetype == "Aggressor":
            scoring = lambda c: CHAMPIONS[c].power_curve["late"]
        elif archetype == "Turtle":
            scoring = lambda c: CHAMPIONS[c].power_curve["early"]
        else:
            scoring = lambda c: sum(CHAMPIONS[c].power_curve.values())
        return max(available, key=scoring)

    # ----- enemy picks ----------------------------------------------------
    async def enemy_picks(self, draft_state: dict, num_picks: int,
                          coach_archetype: str) -> List[str]:
        bans = draft_state.get("blue_bans", []) + draft_state.get("red_bans", [])
        my_picks = draft_state.get("red_picks", [])
        opp_picks = draft_state.get("blue_picks", [])
        available = [c for c in CHAMPIONS
                     if c not in bans and c not in my_picks and c not in opp_picks]

        system = (
            f"You are drafting champions for a 3v3 MOBA team. Your style: "
            f"{coach_archetype}. Pick {num_picks} champion(s) from the available "
            f"pool. Consider team synergy and countering opponent picks. Respond "
            f"with ONLY valid JSON: {{\"picks\": [\"champion_id\", ...], "
            f"\"roles\": {{\"champion_id\": \"role\"}}, \"reasoning\": \"one sentence\"}}"
        )
        user = (
            f"Banned: {bans or 'none'}\n"
            f"Your current picks: {my_picks or 'none'}\n"
            f"Opponent picks: {opp_picks or 'none'}\n\n"
            f"Available champions:\n"
            + "\n".join(_champ_blurb(c) for c in available)
            + f"\n\nPick {num_picks} from the available pool."
        )
        text = await self.generate(system, user, json_mode=True)
        data = _extract_json(text)
        if data and isinstance(data.get("picks"), list):
            picks = [p for p in data["picks"]
                     if isinstance(p, str) and p in available]
            if len(picks) == num_picks:
                return picks
        return self._fallback_picks(available, num_picks, my_picks)

    def _fallback_picks(self, available: List[str], num_picks: int,
                        existing: List[str]) -> List[str]:
        # Prefer picks that fill missing roles and have good synergy
        needed_roles = ["top", "bot", "jungle"]
        # Determine which roles existing picks could plausibly fill
        used_roles: List[str] = []
        for cid in existing:
            for r in CHAMPIONS[cid].roles:
                if r in needed_roles and r not in used_roles:
                    used_roles.append(r)
                    break
        missing = [r for r in needed_roles if r not in used_roles]
        rng = random.Random()
        picks: List[str] = []
        pool = list(available)
        for r in missing:
            cands = [c for c in pool if r in CHAMPIONS[c].roles]
            if cands:
                choice = rng.choice(cands)
                picks.append(choice)
                pool.remove(choice)
            if len(picks) == num_picks:
                return picks
        while len(picks) < num_picks and pool:
            choice = rng.choice(pool)
            picks.append(choice)
            pool.remove(choice)
        return picks

    # ----- enemy strategy -------------------------------------------------
    async def enemy_strategy(self, enemy_team: List[dict],
                             player_team: List[dict],
                             coach_archetype: str) -> dict:
        system = (
            f"You are setting the game strategy for your 3v3 MOBA team. Your "
            f"style: {coach_archetype}. Based on your team comp and the enemy "
            f"comp, output strategy parameters. Respond with ONLY valid JSON:\n"
            "{\n"
            "  \"top_aggression\": 0.0-1.0,\n"
            "  \"bot_aggression\": 0.0-1.0,\n"
            "  \"jungle_top_focus\": 0.0-1.0,\n"
            "  \"jungle_bot_focus\": 0.0-1.0,\n"
            "  \"teamfight_tendency\": 0.0-1.0,\n"
            "  \"objective_priority\": 0.0-1.0,\n"
            "  \"split_push_tendency\": 0.0-1.0\n"
            "}"
        )
        user = (
            f"Your team:\n"
            + "\n".join(f"- {p['role']}: {_champ_blurb(p['champion_id'])[2:]}"
                        for p in enemy_team)
            + "\n\nEnemy team:\n"
            + "\n".join(f"- {p['role']}: {_champ_blurb(p['champion_id'])[2:]}"
                        for p in player_team)
            + "\n\nRelevant matchups:\n"
            + self._matchup_summary(enemy_team, player_team)
        )
        text = await self.generate(system, user, json_mode=True)
        data = _extract_json(text)
        if data:
            return self._validate_params(data)
        return self._fallback_strategy(enemy_team, player_team, coach_archetype)

    def _matchup_summary(self, team_a: List[dict], team_b: List[dict]) -> str:
        a_by = {p["role"]: p["champion_id"] for p in team_a}
        b_by = {p["role"]: p["champion_id"] for p in team_b}
        lines = []
        for role in ("top", "bot", "jungle"):
            if role in a_by and role in b_by:
                m = get_matchup(a_by[role], b_by[role])
                lines.append(f"  {role}: {a_by[role]} vs {b_by[role]} = {m}")
        return "\n".join(lines)

    def _validate_params(self, data: dict) -> dict:
        out = dict(DEFAULT_PARAMS)
        for k in DEFAULT_PARAMS:
            if k in data:
                out[k] = _clamp01(data[k])
        if "analysis" in data:
            out["analysis"] = str(data["analysis"])
        return out

    def _fallback_strategy(self, enemy: List[dict], player: List[dict],
                           archetype: str) -> dict:
        params = dict(DEFAULT_PARAMS)
        if archetype == "Aggressor":
            params["top_aggression"] = 0.8
            params["bot_aggression"] = 0.8
            params["teamfight_tendency"] = 0.7
        elif archetype == "Turtle":
            params["top_aggression"] = 0.3
            params["bot_aggression"] = 0.3
            params["objective_priority"] = 0.7
        return params

    # ----- coaching interpretation ----------------------------------------
    async def interpret_coaching(self, coaching_input: dict,
                                 player_team: List[dict],
                                 enemy_team: List[dict]) -> dict:
        system = (
            "You are a coaching interpreter for a 3v3 MOBA simulation. The "
            "human coach has given instructions for their team. Convert these "
            "into numerical simulation parameters. Consider how the strategy "
            "fits the team composition and matchups. Respond with ONLY valid "
            "JSON:\n"
            "{\n"
            "  \"top_aggression\": 0.0-1.0,\n"
            "  \"bot_aggression\": 0.0-1.0,\n"
            "  \"jungle_top_focus\": 0.0-1.0,\n"
            "  \"jungle_bot_focus\": 0.0-1.0,\n"
            "  \"teamfight_tendency\": 0.0-1.0,\n"
            "  \"objective_priority\": 0.0-1.0,\n"
            "  \"split_push_tendency\": 0.0-1.0,\n"
            "  \"analysis\": \"2-3 sentences explaining how you interpreted the coach's plan\"\n"
            "}"
        )
        user = (
            f"Coaching input:\n{json.dumps(coaching_input, indent=2)}\n\n"
            f"Player team:\n"
            + "\n".join(f"- {p['role']}: {p['champion_id']}" for p in player_team)
            + "\n\nEnemy team:\n"
            + "\n".join(f"- {p['role']}: {p['champion_id']}" for p in enemy_team)
            + "\n\nMatchups:\n"
            + self._matchup_summary(player_team, enemy_team)
        )
        text = await self.generate(system, user, json_mode=True)
        data = _extract_json(text)
        if data:
            return self._validate_params(data)
        out = dict(DEFAULT_PARAMS)
        out["analysis"] = "Falling back to neutral parameters (LLM unavailable)."
        return out

    # ----- narration ------------------------------------------------------
    async def narrate_match(self, match_result: dict,
                            blue_team: List[dict], red_team: List[dict],
                            coaching_input: dict) -> str:
        system = (
            "You are an esports broadcast analyst for a 3v3 MOBA called MOBA "
            "Coach. Narrate the match result in 3-4 paragraphs. Be specific — "
            "reference champion names, key moments, and whether the coach's "
            "strategy worked or failed. Keep it punchy and engaging, like a "
            "real esports cast."
        )
        user = (
            f"Blue team: {[p['champion_id'] for p in blue_team]}\n"
            f"Red team:  {[p['champion_id'] for p in red_team]}\n"
            f"Coach plan:\n{json.dumps(coaching_input, indent=2)}\n\n"
            f"Match result:\n{json.dumps(match_result, indent=2, default=str)}"
        )
        text = await self.generate(system, user, json_mode=False)
        if not text or text == "__LLM_UNAVAILABLE__":
            return self._fallback_narration(match_result, blue_team, red_team)
        return text

    def _fallback_narration(self, result: dict, blue_team: List[dict],
                            red_team: List[dict]) -> str:
        winner = result.get("winner", "?")
        duration = result.get("duration_minutes", "?")
        bk = result.get("blue_kills", "?")
        rk = result.get("red_kills", "?")
        mvp = result.get("mvp", "?")
        bnames = ", ".join(CHAMPIONS[p["champion_id"]].name for p in blue_team)
        rnames = ", ".join(CHAMPIONS[p["champion_id"]].name for p in red_team)
        return (
            f"In a {duration}-minute clash, {bnames} took on {rnames}. "
            f"The {winner} side took the win {bk}-{rk}. "
            f"{CHAMPIONS.get(mvp, CHAMPIONS[list(CHAMPIONS)[0]]).name} was "
            f"the MVP of the match.\n\n(LLM narration unavailable — fallback text.)"
        )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

async def _main():
    logging.basicConfig(level=logging.INFO)
    client = OllamaClient()
    available = await client.is_available()
    print(f"Ollama reachable at {client.base_url}: {available}")

    pool = list(CHAMPIONS.keys())
    ban = await client.enemy_ban(pool, "Aggressor")
    print(f"Enemy ban (Aggressor): {ban}")
    if ban in CHAMPIONS:
        print(f"  -> {CHAMPIONS[ban].name} ({CHAMPIONS[ban].tag})")


if __name__ == "__main__":
    asyncio.run(_main())
