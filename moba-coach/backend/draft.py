"""Draft logic for the 3v3 MOBA.

Flow:
  step 0: player_ban
  step 1: enemy_ban     (LLM)
  step 2: player_pick   (1)
  step 3: enemy_pick    (2, LLM)
  step 4: player_pick   (2)
  step 5: enemy_pick    (1, LLM)
  step 6: role_assignment
  step 7: complete
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

try:
    from .champions import CHAMPIONS
    from .llm import OllamaClient
except ImportError:
    from champions import CHAMPIONS
    from llm import OllamaClient


ARCHETYPES = ["meta_slave", "innovator", "aggressor", "strategist", "turtle"]
VALID_ROLES = {"top", "bot", "jungle"}


class DraftError(Exception):
    pass


class DraftManager:
    def __init__(self, llm: Optional[OllamaClient] = None,
                 archetype: Optional[str] = None):
        self.llm = llm or OllamaClient()
        self.archetype = archetype or random.choice(ARCHETYPES)
        self.blue_bans: List[str] = []
        self.red_bans: List[str] = []
        self.blue_picks: List[str] = []
        self.red_picks: List[str] = []
        self.role_assignments: Dict[str, str] = {}
        self.step: int = 0

    # ----- queries --------------------------------------------------------
    def get_available_champions(self) -> List[str]:
        used = set(self.blue_bans + self.red_bans
                   + self.blue_picks + self.red_picks)
        return [c for c in CHAMPIONS if c not in used]

    def is_complete(self) -> bool:
        return self.step >= 7

    def get_draft_state(self) -> dict:
        return {
            "step": self.step,
            "complete": self.is_complete(),
            "archetype": self.archetype,
            "turn": self._turn(),
            "blue_bans": list(self.blue_bans),
            "red_bans": list(self.red_bans),
            "blue_picks": list(self.blue_picks),
            "red_picks": list(self.red_picks),
            "role_assignments": dict(self.role_assignments),
            "available": self.get_available_champions(),
        }

    def _turn(self) -> str:
        return {
            0: "player_ban",
            1: "enemy_ban",
            2: "player_pick",
            3: "enemy_pick",
            4: "player_pick",
            5: "enemy_pick",
            6: "role_assignment",
            7: "complete",
        }[self.step]

    # ----- bans -----------------------------------------------------------
    def player_ban(self, champion_id: str) -> None:
        if self.step != 0:
            raise DraftError(f"Not player ban step (step={self.step})")
        if champion_id not in self.get_available_champions():
            raise DraftError(f"{champion_id} not available")
        self.blue_bans.append(champion_id)
        self.step = 1

    async def enemy_ban(self) -> str:
        if self.step != 1:
            raise DraftError(f"Not enemy ban step (step={self.step})")
        pool = self.get_available_champions()
        ban = await self.llm.enemy_ban(pool, self.archetype)
        if ban not in pool:
            ban = random.choice(pool)
        self.red_bans.append(ban)
        self.step = 2
        return ban

    # ----- picks ----------------------------------------------------------
    def player_pick(self, champion_id: str) -> None:
        if self.step not in (2, 4):
            raise DraftError(f"Not player pick step (step={self.step})")
        if champion_id not in self.get_available_champions():
            raise DraftError(f"{champion_id} not available")
        self.blue_picks.append(champion_id)
        if self.step == 2:
            self.step = 3
        else:
            # second player pick block — needs 2 picks total (steps 4 & 4)
            if len(self.blue_picks) < 3:
                # still on step 4 expecting one more pick
                return
            self.step = 5

    async def enemy_pick(self) -> List[str]:
        if self.step not in (3, 5):
            raise DraftError(f"Not enemy pick step (step={self.step})")
        num = 2 if self.step == 3 else 1
        state = {
            "blue_bans": self.blue_bans,
            "red_bans": self.red_bans,
            "blue_picks": self.blue_picks,
            "red_picks": self.red_picks,
        }
        picks = await self.llm.enemy_picks(state, num, self.archetype)
        # Validate
        avail = self.get_available_champions()
        clean = [p for p in picks if p in avail]
        # Pad with fallback if LLM returned too few
        if len(clean) < num:
            extras = [c for c in avail if c not in clean]
            random.shuffle(extras)
            clean.extend(extras[: num - len(clean)])
        clean = clean[:num]
        self.red_picks.extend(clean)
        if self.step == 3:
            self.step = 4
        else:
            self.step = 6
        return clean

    # ----- role assignment -----------------------------------------------
    def assign_roles(self, assignments: Dict[str, str]) -> None:
        if self.step != 6:
            raise DraftError(f"Not role assignment step (step={self.step})")
        if set(assignments.keys()) != set(self.blue_picks):
            raise DraftError("Assignments must cover exactly the player's 3 picks")
        roles = list(assignments.values())
        if set(roles) != VALID_ROLES:
            raise DraftError(f"Roles must be exactly {VALID_ROLES}")
        for cid, role in assignments.items():
            if role not in CHAMPIONS[cid].roles:
                raise DraftError(f"{cid} cannot play {role}")
        self.role_assignments = dict(assignments)
        self.step = 7

    def auto_assign_enemy_roles(self) -> Dict[str, str]:
        """Greedy role assignment for the enemy team."""
        picks = list(self.red_picks)
        result: Dict[str, str] = {}
        remaining = set(VALID_ROLES)
        # First pass: champions with only one valid role
        for cid in picks:
            valid = [r for r in CHAMPIONS[cid].roles if r in remaining]
            if len(valid) == 1:
                result[cid] = valid[0]
                remaining.discard(valid[0])
        for cid in picks:
            if cid in result:
                continue
            valid = [r for r in CHAMPIONS[cid].roles if r in remaining]
            if valid:
                result[cid] = valid[0]
                remaining.discard(valid[0])
            else:
                # Forced fallback
                role = remaining.pop() if remaining else CHAMPIONS[cid].roles[0]
                result[cid] = role
        return result


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def main():
        d = DraftManager(archetype="aggressor")
        print(f"archetype: {d.archetype}")
        d.player_ban("rapier")
        print("after player ban:", d.get_draft_state()["blue_bans"])
        await d.enemy_ban()
        print("after enemy ban:", d.get_draft_state()["red_bans"])
        d.player_pick("ironclad")
        print("after player pick 1:", d.blue_picks)
        await d.enemy_pick()
        print("after enemy picks 2:", d.red_picks)
        d.player_pick("solara")
        d.player_pick("fang")
        print("after player picks 2-3:", d.blue_picks)
        await d.enemy_pick()
        print("after enemy pick 1:", d.red_picks)
        d.assign_roles({"ironclad": "top", "solara": "bot", "fang": "jungle"})
        print("complete:", d.is_complete())
        print("enemy roles (auto):", d.auto_assign_enemy_roles())

    asyncio.run(main())
